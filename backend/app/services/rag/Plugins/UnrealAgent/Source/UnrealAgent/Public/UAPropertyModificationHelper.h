// Copyright KuoYu. All Rights Reserved.
// Migrated from SmartUEAssistant - FPropertyModificationHelper -> FUAPropertyModificationHelper

#pragma once

#include "CoreMinimal.h"
#include "UObject/UnrealType.h"
#include "Dom/JsonValue.h"

/**
 * Universal property modification helper for UnrealAgent plugin.
 * Handles all property modifications with proper UE notifications and transactions.
 */
class UNREALAGENT_API FUAPropertyModificationHelper
{
public:
	static bool SetPropertyValue(
		UObject* Object,
		const FString& PropertyPath,
		const TSharedPtr<FJsonValue>& Value,
		bool bCreateTransaction,
		const FString& TransactionDescription,
		FString& OutError
	);

	static FProperty* FindPropertyByPath(UObject* Object, const FString& PropertyPath, UObject*& OutContainer);

	static bool SetPropertyValueDirect(
		FProperty* Property,
		void* ContainerPtr,
		const TSharedPtr<FJsonValue>& Value,
		FString& OutError
	);

	static bool ParseColor(const TSharedPtr<FJsonValue>& Value, FLinearColor& OutColor);
	static bool ParseVector(const TSharedPtr<FJsonValue>& Value, FVector& OutVector);
	static bool ParseRotator(const TSharedPtr<FJsonValue>& Value, FRotator& OutRotator);
	static TSharedPtr<FJsonValue> GetPropertyValueAsJson(FProperty* Property, const void* ContainerPtr);
	static bool IsPropertyEditable(FProperty* Property);
	static FString GetPropertyTypeName(FProperty* Property);
};