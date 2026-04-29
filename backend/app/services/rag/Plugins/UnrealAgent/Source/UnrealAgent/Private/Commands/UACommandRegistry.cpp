// Copyright KuoYu. All Rights Reserved.

#include "Commands/UACommandRegistry.h"
#include "Commands/UACommandBase.h"
#include "Commands/UAProjectCommands.h"
#include "Commands/UAAssetCommands.h"
#include "Commands/UAWorldCommands.h"
#include "Commands/UAActorCommands.h"
#include "Commands/UAViewportCommands.h"
#include "Commands/UAPythonCommands.h"
#include "Commands/UAEditorCommands.h"
#include "Commands/UAMaterialCommands.h"
#include "Commands/UAContextCommands.h"
#include "Commands/UAPropertyCommands.h"
#include "Commands/UABlueprintCommands.h"
#include "Commands/UAAssetManageCommands.h"
#include "Commands/UAScreenshotCommands.h"
#include "Commands/UAEventCommands.h"
// Phase 3: migrated from SmartUEAssistant
#include "Commands/UABatchOperationCommands.h"
#include "Commands/UASceneAnalysisCommands.h"
#include "Commands/UAUniversalModifyCommand.h"
#include "UnrealAgent.h"

UACommandRegistry::UACommandRegistry()
{
	// Original UnrealAgent tools (50 tools)
	RegisterCommand(MakeShared<UAProjectCommands>());
	RegisterCommand(MakeShared<UAAssetCommands>());
	RegisterCommand(MakeShared<UAWorldCommands>());
	RegisterCommand(MakeShared<UAActorCommands>());
	RegisterCommand(MakeShared<UAViewportCommands>());
	RegisterCommand(MakeShared<UAPythonCommands>());
	RegisterCommand(MakeShared<UAEditorCommands>());
	RegisterCommand(MakeShared<UAMaterialCommands>());
	RegisterCommand(MakeShared<UAContextCommands>());
	RegisterCommand(MakeShared<UAPropertyCommands>());
	RegisterCommand(MakeShared<UABlueprintCommands>());
	RegisterCommand(MakeShared<UAAssetManageCommands>());
	RegisterCommand(MakeShared<UAScreenshotCommands>());
	RegisterCommand(MakeShared<UAEventCommands>());
	// Phase 3: batch ops (7), scene analysis (5), universal modify (1)
	RegisterCommand(MakeShared<UABatchOperationCommands>());
	RegisterCommand(MakeShared<UASceneAnalysisCommands>());
	RegisterCommand(MakeShared<UAUniversalModifyCommand>());
}

void UACommandRegistry::RegisterCommand(TSharedPtr<UACommandBase> Command)
{
	if (!Command.IsValid()) return;
	CommandGroups.Add(Command);
	for (const FString& Method : Command->GetSupportedMethods())
	{
		if (MethodMap.Contains(Method))
			UE_LOG(LogUnrealAgent, Warning, TEXT("Method '%s' already registered, overwriting"), *Method);
		MethodMap.Add(Method, Command);
		UE_LOG(LogUnrealAgent, Log, TEXT("Registered method: %s"), *Method);
	}
}

bool UACommandRegistry::Dispatch(
	const FString& MethodName,
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TSharedPtr<UACommandBase>* CommandPtr = MethodMap.Find(MethodName);
	if (!CommandPtr || !CommandPtr->IsValid())
	{
		OutError = FString::Printf(TEXT("Unknown method: %s"), *MethodName);
		return false;
	}
	return (*CommandPtr)->Execute(MethodName, Params, OutResult, OutError);
}

TArray<TSharedPtr<FJsonObject>> UACommandRegistry::GetAllToolSchemas() const
{
	TArray<TSharedPtr<FJsonObject>> Schemas;
	for (const auto& CG : CommandGroups)
	{
		if (!CG.IsValid()) continue;
		for (const FString& Method : CG->GetSupportedMethods())
		{
			TSharedPtr<FJsonObject> Schema = CG->GetToolSchema(Method);
			if (Schema.IsValid()) Schemas.Add(Schema);
		}
	}
	return Schemas;
}

TSharedPtr<FJsonObject> UACommandRegistry::HandleListTools()
{
	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> ToolsArray;
	for (const auto& Schema : GetAllToolSchemas())
		ToolsArray.Add(MakeShared<FJsonValueObject>(Schema));
	Result->SetArrayField(TEXT("tools"), ToolsArray);
	Result->SetNumberField(TEXT("count"), ToolsArray.Num());
	return Result;
}