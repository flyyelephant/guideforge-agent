// Copyright KuoYu. All Rights Reserved.

#include "Commands/UAUniversalModifyCommand.h"
#include "UAPropertyModificationHelper.h"
#include "UnrealAgent.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Components/LightComponent.h"
#include "Engine/Light.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Selection.h"

UAUniversalModifyCommand::UAUniversalModifyCommand() {}

TArray<FString> UAUniversalModifyCommand::GetSupportedMethods() const
{
	return { TEXT("modify_property") };
}

TSharedPtr<FJsonObject> UAUniversalModifyCommand::GetToolSchema(const FString& MethodName) const
{
	TSharedPtr<FJsonObject> Schema = MakeShared<FJsonObject>();
	Schema->SetStringField(TEXT("name"), TEXT("modify_property"));
	Schema->SetStringField(TEXT("description"),
		TEXT("Universal tool to modify any property on any Actor. "
		     "Params: Target (string, e.g. 'selected', 'Light', 'Cube'), "
		     "PropertyName (exact UE property, e.g. 'Intensity', 'LightColor', 'RelativeLocation'), "
		     "Value (number, bool, string color name, or {X,Y,Z} / {R,G,B} object)"));
	return Schema;
}

bool UAUniversalModifyCommand::Execute(
	const FString& MethodName,
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	if (!GEditor) { OutError = TEXT("Editor not available"); return false; }

	FString Target, PropertyName;
	if (!Params->TryGetStringField(TEXT("Target"),       Target))       { OutError = TEXT("Missing 'Target' parameter");       return false; }
	if (!Params->TryGetStringField(TEXT("PropertyName"), PropertyName)) { OutError = TEXT("Missing 'PropertyName' parameter"); return false; }

	TSharedPtr<FJsonValue> Value = Params->Values.FindRef(TEXT("Value"));
	if (!Value.IsValid()) { OutError = TEXT("Missing 'Value' parameter"); return false; }

	TArray<AActor*> Actors = FindTargetActors(Target);
	if (Actors.Num() == 0)
	{
		OutError = FString::Printf(TEXT("No actors found for target: %s"), *Target);
		return false;
	}

	int32 SuccessCount = 0;
	TArray<FString> Errors;

	for (AActor* Actor : Actors)
	{
		FString Err;
		if (ModifyActorProperty(Actor, PropertyName, Value, Err))
			SuccessCount++;
		else
			Errors.AddUnique(Err);
	}

	if (SuccessCount > 0)
	{
		GEditor->RedrawAllViewports();
		GEditor->NoteSelectionChange();
	}

	OutResult = MakeShared<FJsonObject>();
	OutResult->SetNumberField(TEXT("modified"), SuccessCount);
	OutResult->SetNumberField(TEXT("total"),    Actors.Num());
	OutResult->SetStringField(TEXT("message"),
		FString::Printf(TEXT("Modified %d / %d actors"), SuccessCount, Actors.Num()));

	if (SuccessCount == 0)
	{
		OutError = FString::Join(Errors, TEXT("; "));
		return false;
	}
	return true;
}

TArray<AActor*> UAUniversalModifyCommand::FindTargetActors(const FString& TargetDescription)
{
	TArray<AActor*> Results;
	if (!GEditor) return Results;

	FString T = TargetDescription.ToLower();

	// Selected actors
	if (T.Contains(TEXT("selected")) || T.Contains(TEXT("selection")))
	{
		USelection* Sel = GEditor->GetSelectedActors();
		if (Sel) for (FSelectionIterator It(*Sel); It; ++It)
			if (AActor* A = Cast<AActor>(*It)) Results.Add(A);
		return Results;
	}

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) return Results;

	// Lights
	if (T.Contains(TEXT("light")))
	{
		for (TActorIterator<ALight> It(World); It; ++It) Results.Add(*It);
		return Results;
	}

	// General name search
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* A = *It;
		FString Name  = A->GetName().ToLower();
		FString Label = A->GetActorLabel().ToLower();
		if (Name.Contains(T) || Label.Contains(T)) Results.Add(A);
	}
	return Results;
}

bool UAUniversalModifyCommand::ModifyActorProperty(
	AActor* Actor,
	const FString& PropertyPath,
	const TSharedPtr<FJsonValue>& Value,
	FString& OutError)
{
	// Fast path for light color / intensity
	if (Actor->IsA(ALight::StaticClass()))
	{
		ULightComponent* LC = Actor->FindComponentByClass<ULightComponent>();
		if (LC)
		{
			if (PropertyPath.Equals(TEXT("LightColor"), ESearchCase::IgnoreCase) ||
			    PropertyPath.Contains(TEXT("Color")))
			{
				FLinearColor Color;
				if (FUAPropertyModificationHelper::ParseColor(Value, Color))
				{
					FScopedTransaction Transaction(NSLOCTEXT("UnrealAgent", "ModifyProperty", "Modify Property"));
					LC->Modify();
					LC->SetLightColor(Color);
					LC->MarkRenderStateDirty();
					FProperty* P = FindFProperty<FProperty>(LC->GetClass(), TEXT("LightColor"));
					if (P) { FPropertyChangedEvent Ev(P, EPropertyChangeType::ValueSet); LC->PostEditChangeProperty(Ev); }
					return true;
				}
			}
			else if (PropertyPath.Equals(TEXT("Intensity"), ESearchCase::IgnoreCase) &&
			         Value->Type == EJson::Number)
			{
				FScopedTransaction Transaction(NSLOCTEXT("UnrealAgent", "ModifyProperty", "Modify Property"));
				LC->Modify();
				LC->SetIntensity((float)Value->AsNumber());
				LC->MarkRenderStateDirty();
				FProperty* P = FindFProperty<FProperty>(LC->GetClass(), TEXT("Intensity"));
				if (P) { FPropertyChangedEvent Ev(P, EPropertyChangeType::ValueSet); LC->PostEditChangeProperty(Ev); }
				return true;
			}
		}
	}

	// General reflection path
	return FUAPropertyModificationHelper::SetPropertyValue(
		Actor, PropertyPath, Value, true, TEXT("Modify Property"), OutError);
}