// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * xAssistant 插件的自定义日志类别
 * Custom log categories for xAssistant plugin
 * 
 * 用法 / Usage:
 *   UE_LOG(LogSmartUEAssistant, Warning, TEXT("Your message here"));
 *   UE_LOG(LogSmartUEAssistantAI, Log, TEXT("AI response: %s"), *Response);
 */

/** 主插件日志类别 / Main plugin log category */
DECLARE_LOG_CATEGORY_EXTERN(LogSmartUEAssistant, Log, All);

/** AI 服务专用日志类别 / AI Service specific log category */
DECLARE_LOG_CATEGORY_EXTERN(LogSmartUEAssistantAI, Log, All);

/** 编辑器工具日志类别 / Editor tools log category */
DECLARE_LOG_CATEGORY_EXTERN(LogSmartUEAssistantTools, Log, All);

