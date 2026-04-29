// Copyright Epic Games, Inc. All Rights Reserved.
#include "AIService.h"
#include "SmartUEAssistantLog.h"
#include "SmartUEAssistantSettings.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Json.h"
#include "JsonUtilities.h"
#include "Containers/Ticker.h"
#include "HAL/PlatformTime.h"
#include "SceneContextProvider.h"

#define LOCTEXT_NAMESPACE "FAIService"

FAIService& FAIService::Get()
{
    static FAIService Instance;
    return Instance;
}

FAIService::FAIService()
{
    Settings = GetMutableDefault<USmartUEAssistantSettings>();
}

FAIService::~FAIService()
{
    CancelCurrentRequest();
}

void FAIService::SendMessage(const FString& Message, const FOnAIMessageReceived& Callback)
{
    if (Message.IsEmpty()) return;

    // 取消并替换旧请求
    CancelCurrentRequest();
    bCancelRequested = false;
    bTimeoutFired = false;

    // 构建请求体：消息 + 会话历史 + 可选场景摘要
    TSharedPtr<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("message"), Message);

    // 注入会话历史
    if (Settings && Settings->bEnableConversationMemory && Conversation.Num() > 0)
    {
        TArray<TSharedPtr<FJsonValue>> History;
        AppendConversationHistory(History);
        Body->SetArrayField(TEXT("history"), History);
    }

    // 可选注入场景摘要
    if (Settings && Settings->bAutoAttachSceneContext)
    {
        const FString SceneJson = FSceneContextProvider::BuildSceneSummaryJson(Settings);
        if (!SceneJson.IsEmpty())
        {
            Body->SetStringField(TEXT("scene_context"), SceneJson);
        }
    }

    FString BodyStr;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&BodyStr);
    FJsonSerializer::Serialize(Body.ToSharedRef(), Writer);

    // 确定目标 URL
    FString ServerURL = Settings ? Settings->MCPServerURL : TEXT("http://127.0.0.1:8765");
    while (ServerURL.EndsWith(TEXT("/"))) ServerURL.LeftChopInline(1);
    const FString FinalURL = ServerURL + TEXT("/chat");

    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    ActiveRequest = Request;

    Request->SetURL(FinalURL);
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json; charset=utf-8"));
    Request->SetHeader(TEXT("Accept"), TEXT("text/event-stream"));

    {
        FTCHARToUTF8 Convert(*BodyStr);
        TArray<uint8> Payload;
        Payload.Append(reinterpret_cast<const uint8*>(Convert.Get()), Convert.Length());
        Request->SetContent(MoveTemp(Payload));
    }

    Request->OnProcessRequestComplete().BindLambda(
        [this, Callback, UserInput = Message]
        (FHttpRequestPtr Req, FHttpResponsePtr Resp, bool bOk)
        {
            if (TimeoutHandle.IsValid())
            {
                FTSTicker::GetCoreTicker().RemoveTicker(TimeoutHandle);
                TimeoutHandle.Reset();
            }
            if (ActiveRequest.Get() == Req.Get()) ActiveRequest.Reset();

            if (bCancelRequested)
            {
                Callback.ExecuteIfBound(TEXT("[ERR:CANCEL] 已取消：用户主动取消请求"));
                bCancelRequested = false;
                return;
            }
            if (bTimeoutFired)
            {
                Callback.ExecuteIfBound(TEXT("[ERR:TIMEOUT] 超时：请求超过设置的超时时间"));
                bTimeoutFired = false;
                return;
            }

            if (!bOk || !Resp.IsValid())
            {
                Callback.ExecuteIfBound(TEXT("[ERR:NET] 请求失败，请检查 Python MCP Server 是否已启动（http://127.0.0.1:8765）"));
                return;
            }

            const int32 HttpCode = Resp->GetResponseCode();
            if (HttpCode >= 400)
            {
                Callback.ExecuteIfBound(FString::Printf(
                    TEXT("[ERR:SERVER] MCP Server 返回错误（HTTP %d）：%s"),
                    HttpCode, *Resp->GetContentAsString().Left(200)));
                return;
            }

            // 解析 SSE 或普通 JSON 响应
            const FString RawContent = Resp->GetContentAsString();
            FString FinalText;

            // 尝试解析 SSE（data: ... 格式）
            if (RawContent.Contains(TEXT("data:")))
            {
                TArray<FString> Lines;
                RawContent.ParseIntoArrayLines(Lines);
                TArray<FString> Chunks;
                for (const FString& Line : Lines)
                {
                    FString Trimmed = Line.TrimStart();
                    if (Trimmed.StartsWith(TEXT("data:")))
                    {
                        FString Chunk = Trimmed.Mid(5).TrimStart();
                        if (!Chunk.IsEmpty() && Chunk != TEXT("[DONE]"))
                        {
                            // 尝试解析 chunk 为 JSON，提取 content
                            TSharedPtr<FJsonObject> ChunkObj;
                            TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Chunk);
                            if (FJsonSerializer::Deserialize(R, ChunkObj) && ChunkObj.IsValid())
                            {
                                FString Content;
                                if (ChunkObj->TryGetStringField(TEXT("content"), Content))
                                    Chunks.Add(Content);
                                else
                                    Chunks.Add(Chunk);
                            }
                            else
                            {
                                Chunks.Add(Chunk);
                            }
                        }
                    }
                }
                FinalText = FString::Join(Chunks, TEXT(""));
            }
            else
            {
                // 普通 JSON 响应，提取 response 字段
                TSharedPtr<FJsonObject> RespObj;
                TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(RawContent);
                if (FJsonSerializer::Deserialize(R, RespObj) && RespObj.IsValid())
                {
                    if (!RespObj->TryGetStringField(TEXT("response"), FinalText))
                        FinalText = RawContent;
                }
                else
                {
                    FinalText = RawContent;
                }
            }

            if (Settings && Settings->bEnableConversationMemory)
            {
                PushUserMessage(UserInput);
                PushAssistantMessage(FinalText);
                TrimConversation();
            }

            Callback.ExecuteIfBound(FinalText);
        }
    );

    // 超时 Ticker（30 秒）
    const double StartTime = FPlatformTime::Seconds();
    const int32 TimeoutSec = 30;
    TimeoutHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateLambda([this, StartTime, TimeoutSec](float) -> bool
        {
            if ((FPlatformTime::Seconds() - StartTime) >= TimeoutSec)
            {
                if (ActiveRequest.IsValid())
                {
                    bTimeoutFired = true;
                    ActiveRequest->CancelRequest();
                }
                return false;
            }
            return true;
        }), 0.2f);

    Request->ProcessRequest();
}

void FAIService::CancelCurrentRequest()
{
    if (TimeoutHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TimeoutHandle);
        TimeoutHandle.Reset();
    }
    if (ActiveRequest.IsValid())
    {
        bCancelRequested = true;
        ActiveRequest->CancelRequest();
        ActiveRequest.Reset();
    }
}

void FAIService::ClearConversationMemory()
{
    Conversation.Reset();
}

void FAIService::AppendConversationHistory(TArray<TSharedPtr<FJsonValue>>& InOutMessages) const
{
    if (!Settings || Settings->MaxConversationRounds <= 0) return;
    const int32 MaxKeep = Settings->MaxConversationRounds * 2;
    const int32 Start = FMath::Max(0, Conversation.Num() - MaxKeep);
    for (int32 i = Start; i < Conversation.Num(); ++i)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetStringField(TEXT("role"), Conversation[i].Role);
        Obj->SetStringField(TEXT("content"), Conversation[i].Content);
        InOutMessages.Add(MakeShared<FJsonValueObject>(Obj));
    }
}

void FAIService::PushUserMessage(const FString& Content)
{
    Conversation.Add({TEXT("user"), Content});
}

void FAIService::PushAssistantMessage(const FString& Content)
{
    Conversation.Add({TEXT("assistant"), Content});
}

void FAIService::TrimConversation()
{
    if (!Settings || Settings->MaxConversationRounds <= 0) { Conversation.Reset(); return; }
    const int32 MaxKeep = Settings->MaxConversationRounds * 2;
    const int32 Over = Conversation.Num() - MaxKeep;
    if (Over > 0) Conversation.RemoveAt(0, Over, EAllowShrinking::No);
}

#undef LOCTEXT_NAMESPACE