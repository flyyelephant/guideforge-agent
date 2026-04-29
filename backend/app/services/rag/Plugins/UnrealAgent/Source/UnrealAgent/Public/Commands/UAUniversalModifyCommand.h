// Copyright KuoYu. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Commands/UACommandBase.h"

/**
 * Universal modify command for UnrealAgent.
 * One tool to modify any property on any Actor using AI semantic targeting.
 * Implements: modify_property
 */
class UAUniversalModifyCommand : public UACommandBase
{
public:
	UAUniversalModifyCommand();

	virtual TArray<FString> GetSupportedMethods() const override;
	virtual TSharedPtr<FJsonObject> GetToolSchema(const FString& MethodName) const override;
	virtual bool Execute(
		const FString& MethodName,
		const TSharedPtr<FJsonObject>& Params,
		TSharedPtr<FJsonObject>& OutResult,
		FString& OutError
	) override;

private:
	TArray<AActor*> FindTargetActors(const FString& TargetDescription);
	bool ModifyActorProperty(AActor* Actor, const FString& PropertyPath, const TSharedPtr<FJsonValue>& Value, FString& OutError);
};