// Copyright Epic Games, Inc. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"

class IHttpRequest;

DECLARE_DELEGATE_OneParam(FOnAIMessageReceived, const FString& /*Response*/);

class FAIService
{
public:
    static FAIService& Get();
    ~FAIService();

    // 发送消息到本地 Python HTTP Server，接收 SSE 流式响应
    void SendMessage(const FString& Message, const FOnAIMessageReceived& Callback);

    // 取消当前活动请求
    void CancelCurrentRequest();

    // 检查是否有活动请求
    bool HasActiveRequest() const { return ActiveRequest.IsValid(); }

    // 清除会话历史
    void ClearConversationMemory();

    // 以下接口保留空实现以兼容 Window 的残留调用，后续统一删除
    bool HasPendingConfirmation() const { return false; }
    void ConfirmPendingPlan(const FOnAIMessageReceived&) {}
    void CancelPendingPlan() {}

private:
    FAIService();

    class USmartUEAssistantSettings* Settings;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> ActiveRequest;
    FTSTicker::FDelegateHandle TimeoutHandle;
    bool bCancelRequested = false;
    bool bTimeoutFired = false;

    struct FConvMsg { FString Role; FString Content; };
    TArray<FConvMsg> Conversation;

    void AppendConversationHistory(TArray<TSharedPtr<FJsonValue>>& InOutMessages) const;
    void PushUserMessage(const FString& Content);
    void PushAssistantMessage(const FString& Content);
    void TrimConversation();
};