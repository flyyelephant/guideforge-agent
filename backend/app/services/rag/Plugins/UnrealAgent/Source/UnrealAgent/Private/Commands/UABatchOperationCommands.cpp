// Copyright KuoYu. All Rights Reserved.

#include "Commands/UABatchOperationCommands.h"
#include "UnrealAgent.h"
#include "Editor.h"
#include "Selection.h"
#include "Engine/Selection.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"
#include "EditorLevelUtils.h"
#include "Components/SceneComponent.h"

UABatchOperationCommands::UABatchOperationCommands() {}

TArray<FString> UABatchOperationCommands::GetSupportedMethods() const
{
	return {
		TEXT("batch_rename_actors"),
		TEXT("batch_set_visibility"),
		TEXT("batch_set_mobility"),
		TEXT("batch_move_to_level"),
		TEXT("batch_set_tags"),
		TEXT("align_to_ground"),
		TEXT("distribute_actors")
	};
}

TSharedPtr<FJsonObject> UABatchOperationCommands::GetToolSchema(const FString& MethodName) const
{
	TSharedPtr<FJsonObject> Schema = MakeShared<FJsonObject>();
	Schema->SetStringField(TEXT("name"), MethodName);

	if (MethodName == TEXT("batch_rename_actors"))
		Schema->SetStringField(TEXT("description"), TEXT("Batch rename selected actors with optional prefix, suffix, and numbering"));
	else if (MethodName == TEXT("batch_set_visibility"))
		Schema->SetStringField(TEXT("description"), TEXT("Batch set visibility for selected actors"));
	else if (MethodName == TEXT("batch_set_mobility"))
		Schema->SetStringField(TEXT("description"), TEXT("Batch set mobility (Static/Stationary/Movable) for selected actors"));
	else if (MethodName == TEXT("batch_move_to_level"))
		Schema->SetStringField(TEXT("description"), TEXT("Move selected actors to a specific level"));
	else if (MethodName == TEXT("batch_set_tags"))
		Schema->SetStringField(TEXT("description"), TEXT("Batch set, add, or remove tags for selected actors"));
	else if (MethodName == TEXT("align_to_ground"))
		Schema->SetStringField(TEXT("description"), TEXT("Align selected actors to ground/surface"));
	else if (MethodName == TEXT("distribute_actors"))
		Schema->SetStringField(TEXT("description"), TEXT("Distribute selected actors in Line, Grid, Circle, or Random pattern"));

	return Schema;
}

bool UABatchOperationCommands::Execute(
	const FString& MethodName,
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	if (MethodName == TEXT("batch_rename_actors"))   return BatchRenameActors(Params, OutResult, OutError);
	if (MethodName == TEXT("batch_set_visibility"))  return BatchSetVisibility(Params, OutResult, OutError);
	if (MethodName == TEXT("batch_set_mobility"))    return BatchSetMobility(Params, OutResult, OutError);
	if (MethodName == TEXT("batch_move_to_level"))   return BatchMoveToLevel(Params, OutResult, OutError);
	if (MethodName == TEXT("batch_set_tags"))        return BatchSetTags(Params, OutResult, OutError);
	if (MethodName == TEXT("align_to_ground"))       return AlignToGround(Params, OutResult, OutError);
	if (MethodName == TEXT("distribute_actors"))     return DistributeActors(Params, OutResult, OutError);

	OutError = FString::Printf(TEXT("Unknown method: %s"), *MethodName);
	return false;
}

// ── Helpers ────────────────────────────────────────────────────────────────

static TArray<AActor*> GetSelectedActors()
{
	TArray<AActor*> Result;
	if (!GEditor) return Result;
	USelection* Sel = GEditor->GetSelectedActors();
	if (!Sel) return Result;
	for (FSelectionIterator It(*Sel); It; ++It)
		if (AActor* A = Cast<AActor>(*It)) Result.Add(A);
	return Result;
}

static TSharedPtr<FJsonObject> MakeCountResult(const FString& Message, int32 Count)
{
	TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
	R->SetStringField(TEXT("message"), Message);
	R->SetNumberField(TEXT("count"), Count);
	return R;
}

// ── Implementations ────────────────────────────────────────────────────────

bool UABatchOperationCommands::BatchRenameActors(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	FString Prefix      = Params->HasField(TEXT("Prefix"))      ? Params->GetStringField(TEXT("Prefix"))      : TEXT("");
	FString Suffix      = Params->HasField(TEXT("Suffix"))      ? Params->GetStringField(TEXT("Suffix"))      : TEXT("");
	FString RemovePrefix= Params->HasField(TEXT("RemovePrefix"))? Params->GetStringField(TEXT("RemovePrefix")): TEXT("");
	bool bUseIndex  = Params->HasField(TEXT("StartIndex"));
	int32 StartIndex = bUseIndex ? (int32)Params->GetNumberField(TEXT("StartIndex")) : 0;

	int32 Count = 0;
	int32 Idx = StartIndex;
	for (AActor* Actor : Actors)
	{
		FString Name = Actor->GetActorLabel();
		if (!RemovePrefix.IsEmpty() && Name.StartsWith(RemovePrefix))
			Name = Name.RightChop(RemovePrefix.Len());

		FString Final;
		if (!Prefix.IsEmpty()) Final += Prefix;
		if (bUseIndex)
		{
			Final += FString::Printf(TEXT("%s%d"), !Prefix.IsEmpty() ? TEXT("_") : TEXT(""), Idx++);
			if (!Name.IsEmpty()) Final += TEXT("_") + Name;
		}
		else Final += Name;
		if (!Suffix.IsEmpty()) Final += Suffix;

		Actor->SetActorLabel(Final);
		Count++;
	}

	OutResult = MakeCountResult(FString::Printf(TEXT("Renamed %d actors"), Count), Count);
	return true;
}

bool UABatchOperationCommands::BatchSetVisibility(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	bool bVisible = Params->GetBoolField(TEXT("Visible"));
	bool bChildren = Params->HasField(TEXT("ApplyToChildren")) ? Params->GetBoolField(TEXT("ApplyToChildren")) : true;

	int32 Count = 0;
	for (AActor* Actor : Actors)
	{
		Actor->SetActorHiddenInGame(!bVisible);
		Actor->SetIsTemporarilyHiddenInEditor(!bVisible);
		Count++;
		if (bChildren)
		{
			TArray<AActor*> ChildActors;
			Actor->GetAllChildActors(ChildActors, true);
			for (AActor* Child : ChildActors)
			{
				Child->SetActorHiddenInGame(!bVisible);
				Child->SetIsTemporarilyHiddenInEditor(!bVisible);
				Count++;
			}
		}
	}

	OutResult = MakeCountResult(
		FString::Printf(TEXT("Set %d actors to %s"), Count, bVisible ? TEXT("Visible") : TEXT("Hidden")), Count);
	return true;
}

bool UABatchOperationCommands::BatchSetMobility(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	FString MobilityStr = Params->GetStringField(TEXT("Mobility"));
	EComponentMobility::Type Mobility;

	if      (MobilityStr.Equals(TEXT("Static"),      ESearchCase::IgnoreCase)) Mobility = EComponentMobility::Static;
	else if (MobilityStr.Equals(TEXT("Stationary"),  ESearchCase::IgnoreCase)) Mobility = EComponentMobility::Stationary;
	else if (MobilityStr.Equals(TEXT("Movable"),     ESearchCase::IgnoreCase)) Mobility = EComponentMobility::Movable;
	else { OutError = FString::Printf(TEXT("Invalid mobility: %s"), *MobilityStr); return false; }

	int32 Count = 0;
	for (AActor* Actor : Actors)
		if (USceneComponent* Root = Actor->GetRootComponent())
		{ Root->SetMobility(Mobility); Count++; }

	OutResult = MakeCountResult(FString::Printf(TEXT("Set mobility to %s for %d actors"), *MobilityStr, Count), Count);
	return true;
}

bool UABatchOperationCommands::BatchMoveToLevel(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	FString LevelName = Params->GetStringField(TEXT("LevelName"));
	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) { OutError = TEXT("No world available"); return false; }

	ULevel* TargetLevel = nullptr;
	for (ULevel* Level : World->GetLevels())
		if (Level && Level->GetOuter()->GetName().Contains(LevelName))
		{ TargetLevel = Level; break; }

	if (!TargetLevel) { OutError = FString::Printf(TEXT("Level not found: %s"), *LevelName); return false; }

	UEditorLevelUtils::MoveActorsToLevel(Actors, TargetLevel);

	OutResult = MakeCountResult(FString::Printf(TEXT("Moved %d actors to %s"), Actors.Num(), *LevelName), Actors.Num());
	return true;
}

bool UABatchOperationCommands::BatchSetTags(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	FString Mode = Params->GetStringField(TEXT("Mode"));
	const TArray<TSharedPtr<FJsonValue>>* TagsArray;
	if (!Params->TryGetArrayField(TEXT("Tags"), TagsArray))
	{ OutError = TEXT("Tags must be an array"); return false; }

	TArray<FName> Tags;
	for (auto& TV : *TagsArray) Tags.Add(FName(*TV->AsString()));

	int32 Count = 0;
	for (AActor* Actor : Actors)
	{
		if      (Mode.Equals(TEXT("Set"),    ESearchCase::IgnoreCase)) { Actor->Tags.Empty(); Actor->Tags.Append(Tags); }
		else if (Mode.Equals(TEXT("Add"),    ESearchCase::IgnoreCase)) { for (FName T : Tags) Actor->Tags.AddUnique(T); }
		else if (Mode.Equals(TEXT("Remove"), ESearchCase::IgnoreCase)) { for (FName T : Tags) Actor->Tags.Remove(T); }
		else { OutError = FString::Printf(TEXT("Invalid mode: %s"), *Mode); return false; }
		Count++;
	}

	OutResult = MakeCountResult(FString::Printf(TEXT("%s tags for %d actors"), *Mode, Count), Count);
	return true;
}

bool UABatchOperationCommands::AlignToGround(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	bool  bAlignRot = Params->HasField(TEXT("AlignRotation")) ? Params->GetBoolField(TEXT("AlignRotation")) : false;
	float Offset    = Params->HasField(TEXT("Offset"))        ? (float)Params->GetNumberField(TEXT("Offset")) : 0.0f;

	UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World) { OutError = TEXT("No world available"); return false; }

	int32 Count = 0;
	for (AActor* Actor : Actors)
	{
		FVector Loc = Actor->GetActorLocation();
		FHitResult Hit;
		FCollisionQueryParams QP;
		QP.AddIgnoredActor(Actor);

		if (World->LineTraceSingleByChannel(Hit, Loc + FVector(0,0,1000), Loc - FVector(0,0,10000), ECC_WorldStatic, QP))
		{
			Actor->SetActorLocation(Hit.Location + FVector(0, 0, Offset));
			if (bAlignRot && Hit.Normal.SizeSquared() > 0.01f)
			{
				FRotator Rot = Hit.Normal.Rotation();
				Rot.Pitch -= 90.0f;
				Actor->SetActorRotation(Rot);
			}
			Count++;
		}
	}

	OutResult = MakeCountResult(FString::Printf(TEXT("Aligned %d actors to ground"), Count), Count);
	return true;
}

bool UABatchOperationCommands::DistributeActors(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	TArray<AActor*> Actors = GetSelectedActors();
	if (Actors.Num() == 0) { OutError = TEXT("No actors selected"); return false; }

	FString Pattern = Params->GetStringField(TEXT("Pattern"));
	float   Spacing = (float)Params->GetNumberField(TEXT("Spacing"));
	FVector Center  = Actors[0]->GetActorLocation();

	if (Pattern.Equals(TEXT("Line"), ESearchCase::IgnoreCase))
	{
		for (int32 i = 0; i < Actors.Num(); ++i)
			Actors[i]->SetActorLocation(Center + FVector(i * Spacing, 0, 0));
	}
	else if (Pattern.Equals(TEXT("Grid"), ESearchCase::IgnoreCase))
	{
		int32 Cols = Params->HasField(TEXT("Columns")) ? (int32)Params->GetNumberField(TEXT("Columns")) : 5;
		for (int32 i = 0; i < Actors.Num(); ++i)
			Actors[i]->SetActorLocation(Center + FVector((i % Cols) * Spacing, (i / Cols) * Spacing, 0));
	}
	else if (Pattern.Equals(TEXT("Circle"), ESearchCase::IgnoreCase))
	{
		float Radius = Params->HasField(TEXT("Radius")) ? (float)Params->GetNumberField(TEXT("Radius")) : Spacing * Actors.Num() / (2 * PI);
		for (int32 i = 0; i < Actors.Num(); ++i)
		{
			float Angle = (2 * PI * i) / Actors.Num();
			Actors[i]->SetActorLocation(Center + FVector(FMath::Cos(Angle) * Radius, FMath::Sin(Angle) * Radius, 0));
		}
	}
	else if (Pattern.Equals(TEXT("Random"), ESearchCase::IgnoreCase))
	{
		for (int32 i = 1; i < Actors.Num(); ++i)
			Actors[i]->SetActorLocation(Center + FVector(FMath::FRandRange(-Spacing, Spacing), FMath::FRandRange(-Spacing, Spacing), 0));
	}
	else { OutError = FString::Printf(TEXT("Invalid pattern: %s"), *Pattern); return false; }

	OutResult = MakeCountResult(FString::Printf(TEXT("Distributed %d actors in %s pattern"), Actors.Num(), *Pattern), Actors.Num());
	return true;
}