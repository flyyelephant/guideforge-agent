// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Widgets/Docking/SDockTab.h"
#include "SmartUEAssistantCommands.h"

/**
 * xAssistant 主模块
 * xAssistant main module
 * 
 * 管理插件生命周期、UI 注册和编辑器集成。
 * 为虚幻引擎开发提供 AI 驱动的辅助。
 * 
 * Manages plugin lifecycle, UI registration, and editor integration.
 * Provides AI-powered assistance for Unreal Engine development.
 */
class FSmartUEAssistantModule : public IModuleInterface
{
public:
	/** 模块加载时调用 / Called when module is loaded */
	virtual void StartupModule() override;
	
	/** 模块卸载时调用 / Called when module is unloaded */
	virtual void ShutdownModule() override;
	
private:
	/** 注册编辑器菜单和命令 / Register editor menus and commands */
	void RegisterMenus();
	
	/** 以可停靠标签页的形式打开 AI 助手窗口 / Open AI assistant window as dockable tab */
	void OpenAIAssistantWindow();

	/**
	 * 生成插件标签页内容
	 * Spawn the plugin tab content
	 * 
	 * @param Args 标签页管理器的生成参数 / Spawn arguments from tab manager
	 * @return 新的停靠标签页实例 / New dock tab instance
	 */
	TSharedRef<SDockTab> OnSpawnPluginTab(const FSpawnTabArgs& Args);
	
	/** 插件操作的 UI 命令列表 / UI command list for plugin actions */
	TSharedPtr<class FUICommandList> PluginCommands;

	/** 可停靠标签页的唯一名称 / Unique name for the dockable tab */
	static FName TabName;
};