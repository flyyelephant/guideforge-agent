// 插件设置类实现文件
#include "SmartUEAssistantSettings.h"

USmartUEAssistantSettings::USmartUEAssistantSettings()
{
	// MCP Server
	MCPServerURL = TEXT("http://127.0.0.1:8765");

	// 场景上下文默认值
	bAutoAttachSceneContext = true;
	MaxActorsInSummary = 100;
	bIncludeViewportCamera = true;
	bIncludeComponentSummary = true;

	// 确认关键词
	bEnterAcceptsPending = true;
	ConfirmAcceptKeywords = TEXT("确认,执行,同意,继续,ok,yes");
	ConfirmCancelKeywords = TEXT("取消,放弃,中止,no");

	// 会话记忆默认：启用，最大轮次6
	bEnableConversationMemory = true;
	MaxConversationRounds = 6;
}