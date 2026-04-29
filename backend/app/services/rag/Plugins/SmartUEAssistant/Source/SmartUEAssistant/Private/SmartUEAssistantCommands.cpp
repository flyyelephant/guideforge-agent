// SmartUEAssistant 命令实现
#include "SmartUEAssistantCommands.h"
#include "InputCoreTypes.h"

#define LOCTEXT_NAMESPACE "FSmartUEAssistantCommands"

void FSmartUEAssistantCommands::RegisterCommands()
{
    UI_COMMAND(OpenCommandPanel, "xAssistant", "Open the xAssistant window (Command Panel)", EUserInterfaceActionType::Button, FInputChord(EKeys::K, EModifierKey::Control | EModifierKey::Alt));
}

#undef LOCTEXT_NAMESPACE