// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "SmartUEAssistantSettings.generated.h"

/**
 * SmartUEAssistant 插件设置
 * 设置存储在 Config/DefaultSmartUEAssistant.ini
 */
UCLASS(Config=SmartUEAssistant, DefaultConfig)
class SMARTUEASSISTANT_API USmartUEAssistantSettings : public UObject
{
	GENERATED_BODY()

public:
	USmartUEAssistantSettings();

	/** 本地 Python MCP HTTP Server 地址 */
	UPROPERTY(Config, EditAnywhere, Category="MCP Server",
		meta=(Tooltip="本地 Python MCP HTTP Server 地址，默认 http://127.0.0.1:8765"))
	FString MCPServerURL = TEXT("http://127.0.0.1:8765");

	/** Automatically attach scene summary when sending messages in editor */
	UPROPERTY(EditAnywhere, Config, Category="AI", meta=(Tooltip="Include scene context in AI queries"))
	bool bAutoAttachSceneContext = true;

	/** Maximum number of actors to include in scene summary per level */
	UPROPERTY(EditAnywhere, Config, Category="AI", meta=(ClampMin="1", ClampMax="500", Tooltip="Max actors in scene context"))
	int32 MaxActorsInSummary = 100;

	/** Include viewport camera position and rotation in scene context */
	UPROPERTY(EditAnywhere, Config, Category="AI", meta=(Tooltip="Include camera position in context"))
	bool bIncludeViewportCamera = true;

	/** Include component count information in scene summary */
	UPROPERTY(EditAnywhere, Config, Category="AI", meta=(Tooltip="Include component summary"))
	bool bIncludeComponentSummary = true;

	/** Allow empty Enter key to confirm pending dangerous operations */
	UPROPERTY(EditAnywhere, Config, Category="Confirm", meta=(Tooltip="Press Enter to confirm pending operations"))
	bool bEnterAcceptsPending = true;

	/** Comma-separated keywords that confirm pending operations */
	UPROPERTY(EditAnywhere, Config, Category="Confirm", meta=(Tooltip="Keywords to confirm (comma-separated)"))
	FString ConfirmAcceptKeywords = TEXT("确认,执行,同意,继续,ok,yes");

	/** Comma-separated keywords that cancel pending operations */
	UPROPERTY(EditAnywhere, Config, Category="Confirm", meta=(Tooltip="Keywords to cancel (comma-separated)"))
	FString ConfirmCancelKeywords = TEXT("取消,放弃,中止,no");

	/** Enable conversation memory to maintain context across messages */
	UPROPERTY(EditAnywhere, Config, Category="AI|Memory", meta=(Tooltip="Remember previous conversation"))
	bool bEnableConversationMemory = true;

	/** Maximum number of conversation rounds to keep in memory (0 = no history) */
	UPROPERTY(EditAnywhere, Config, Category="AI|Memory", meta=(ClampMin="0", ClampMax="50", Tooltip="Max conversation rounds to remember"))
	int32 MaxConversationRounds = 6;
};