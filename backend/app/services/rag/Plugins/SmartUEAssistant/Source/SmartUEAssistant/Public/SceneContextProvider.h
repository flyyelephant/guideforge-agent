/**
 * 场景上下文采集提供者（编辑器专用）
 * Scene context collection provider (Editor only)
 */
#pragma once

#include "CoreMinimal.h"

class USmartUEAssistantSettings;

/**
 * 轻量静态工具类：采集当前关卡、选中Actor与视口相机，生成简要JSON
 * Lightweight static utility: Collects current level, selected actors, and viewport camera to generate brief JSON
 */
struct FSceneContextProvider
{
	/**
	 * 返回可内嵌到提示词的JSON摘要（失败时返回空字符串）
	 * Returns JSON summary that can be embedded in prompts (returns empty string on failure)
	 * 
	 * @param Settings 插件设置，控制采集行为 / Plugin settings that control collection behavior
	 * @return JSON格式的场景摘要 / Scene summary in JSON format
	 */
	static FString BuildSceneSummaryJson(const USmartUEAssistantSettings* Settings);
};