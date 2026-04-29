/**
 * SmartUEAssistant 命令定义（TCommands）
 * SmartUEAssistant command definitions (TCommands)
 */
#pragma once

#include "CoreMinimal.h"
#include "Framework/Commands/Commands.h"
#include "Framework/Commands/UICommandInfo.h"
#include "SmartUEAssistantStyle.h"

/**
 * xAssistant 的 UI 命令集
 * UI command set for xAssistant
 */
class FSmartUEAssistantCommands : public TCommands<FSmartUEAssistantCommands>
{
public:
    FSmartUEAssistantCommands()
        : TCommands<FSmartUEAssistantCommands>(
            TEXT("SmartUEAssistant"),
            NSLOCTEXT("SmartUEAssistant", "Commands", "xAssistant Commands"),
            NAME_None,
            FSmartUEAssistantStyle::GetStyleSetName())
    {}

    virtual void RegisterCommands() override;

public:
    /** 打开命令面板/助手窗口 / Open command panel/assistant window */
    TSharedPtr<FUICommandInfo> OpenCommandPanel;
};