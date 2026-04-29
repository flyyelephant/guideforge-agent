// Copyright KuoYu. All Rights Reserved.
// Migrated from SmartUEAssistant BatchOperationTools -> UACommandBase interface

#pragma once

#include "CoreMinimal.h"
#include "Commands/UACommandBase.h"

/**
 * Batch operation commands for UnrealAgent.
 * Implements: batch_rename_actors, batch_set_visibility, batch_set_mobility,
 *             batch_move_to_level, batch_set_tags, align_to_ground, distribute_actors
 */
class UABatchOperationCommands : public UACommandBase
{
public:
	UABatchOperationCommands();

	virtual TArray<FString> GetSupportedMethods() const override;
	virtual TSharedPtr<FJsonObject> GetToolSchema(const FString& MethodName) const override;
	virtual bool Execute(
		const FString& MethodName,
		const TSharedPtr<FJsonObject>& Params,
		TSharedPtr<FJsonObject>& OutResult,
		FString& OutError
	) override;

private:
	bool BatchRenameActors(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
	bool BatchSetVisibility(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
	bool BatchSetMobility(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
	bool BatchMoveToLevel(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
	bool BatchSetTags(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
	bool AlignToGround(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
	bool DistributeActors(const TSharedPtr<FJsonObject>& Params, TSharedPtr<FJsonObject>& OutResult, FString& OutError);
};