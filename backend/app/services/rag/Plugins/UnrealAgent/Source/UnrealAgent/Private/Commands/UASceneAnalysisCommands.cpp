// Copyright KuoYu. All Rights Reserved.

#include "Commands/UASceneAnalysisCommands.h"
#include "UnrealAgent.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/Light.h"
#include "Components/StaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Engine/StaticMesh.h"

UASceneAnalysisCommands::UASceneAnalysisCommands() {}

TArray<FString> UASceneAnalysisCommands::GetSupportedMethods() const
{
	return {
		TEXT("analyze_level_stats"),
		TEXT("find_missing_references"),
		TEXT("find_duplicate_names"),
		TEXT("find_oversized_meshes"),
		TEXT("validate_level")
	};
}

TSharedPtr<FJsonObject> UASceneAnalysisCommands::GetToolSchema(const FString& MethodName) const
{
	TSharedPtr<FJsonObject> Schema = MakeShared<FJsonObject>();
	Schema->SetStringField(TEXT("name"), MethodName);
	if (MethodName == TEXT("analyze_level_stats"))
		Schema->SetStringField(TEXT("description"), TEXT("Analyze current level: actor counts, vertices, triangles, lights, mobility"));
	else if (MethodName == TEXT("find_missing_references"))
		Schema->SetStringField(TEXT("description"), TEXT("Find actors with missing mesh or material references"));
	else if (MethodName == TEXT("find_duplicate_names"))
		Schema->SetStringField(TEXT("description"), TEXT("Find duplicate actor labels in the level"));
	else if (MethodName == TEXT("find_oversized_meshes"))
		Schema->SetStringField(TEXT("description"), TEXT("Find high-poly static meshes above a vertex threshold (default 50000)"));
	else if (MethodName == TEXT("validate_level"))
		Schema->SetStringField(TEXT("description"), TEXT("Validate level for common issues: no collision, high-poly movable, actors outside bounds"));
	return Schema;
}

bool UASceneAnalysisCommands::Execute(
	const FString& MethodName,
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	if (MethodName == TEXT("analyze_level_stats"))      return AnalyzeLevelStats(Params, OutResult, OutError);
	if (MethodName == TEXT("find_missing_references"))  return FindMissingReferences(Params, OutResult, OutError);
	if (MethodName == TEXT("find_duplicate_names"))     return FindDuplicateNames(Params, OutResult, OutError);
	if (MethodName == TEXT("find_oversized_meshes"))    return FindOversizedMeshes(Params, OutResult, OutError);
	if (MethodName == TEXT("validate_level"))           return ValidateLevel(Params, OutResult, OutError);
	OutError = FString::Printf(TEXT("Unknown method: %s"), *MethodName);
	return false;
}

bool UASceneAnalysisCommands::AnalyzeLevelStats(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) { OutError = TEXT("No world available"); return false; }

	TMap<FString, int32> ActorCounts;
	int32 Total = 0, StaticN = 0, StationaryN = 0, MovableN = 0, LightN = 0;
	int64 TotalVerts = 0, TotalTris = 0;

	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (!IsValid(Actor)) continue;
		Total++;
		ActorCounts.FindOrAdd(Actor->GetClass()->GetName())++;
		if (USceneComponent* R = Actor->GetRootComponent())
		{
			switch (R->Mobility)
			{
			case EComponentMobility::Static:      StaticN++;     break;
			case EComponentMobility::Stationary:  StationaryN++; break;
			case EComponentMobility::Movable:     MovableN++;    break;
			}
		}
		if (Cast<ALight>(Actor)) LightN++;
		if (AStaticMeshActor* SMA = Cast<AStaticMeshActor>(Actor))
			if (UStaticMeshComponent* MC = SMA->GetStaticMeshComponent())
				if (UStaticMesh* SM = MC->GetStaticMesh())
					if (SM->GetRenderData() && SM->GetRenderData()->LODResources.Num() > 0)
					{
						const FStaticMeshLODResources& LOD0 = SM->GetRenderData()->LODResources[0];
						TotalVerts += LOD0.GetNumVertices();
						TotalTris  += LOD0.GetNumTriangles();
					}
	}

	ActorCounts.ValueSort([](int32 A, int32 B){ return A > B; });
	TArray<FString> TopClasses;
	int32 C = 0;
	for (const auto& P : ActorCounts)
	{ TopClasses.Add(FString::Printf(TEXT("  %s: %d"), *P.Key, P.Value)); if (++C >= 10) break; }

	OutResult = MakeShared<FJsonObject>();
	OutResult->SetNumberField(TEXT("TotalActors"),      Total);
	OutResult->SetNumberField(TEXT("StaticActors"),     StaticN);
	OutResult->SetNumberField(TEXT("StationaryActors"), StationaryN);
	OutResult->SetNumberField(TEXT("MovableActors"),    MovableN);
	OutResult->SetNumberField(TEXT("LightCount"),       LightN);
	OutResult->SetNumberField(TEXT("TotalVertices"),    (double)TotalVerts);
	OutResult->SetNumberField(TEXT("TotalTriangles"),   (double)TotalTris);
	OutResult->SetStringField(TEXT("message"), FString::Printf(
		TEXT("Total: %d | Static: %d | Stationary: %d | Movable: %d | Lights: %d | Verts: %lld | Tris: %lld"),
		Total, StaticN, StationaryN, MovableN, LightN, TotalVerts, TotalTris));
	return true;
}

bool UASceneAnalysisCommands::FindMissingReferences(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) { OutError = TEXT("No world available"); return false; }

	TArray<FString> Missing;
	for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
	{
		AStaticMeshActor* A = *It;
		if (!IsValid(A)) continue;
		UStaticMeshComponent* MC = A->GetStaticMeshComponent();
		if (!MC) continue;
		bool bMissing = !MC->GetStaticMesh();
		if (!bMissing)
			for (int32 i = 0; i < MC->GetNumMaterials(); ++i)
				if (!MC->GetMaterial(i)) { bMissing = true; break; }
		if (bMissing)
			Missing.Add(FString::Printf(TEXT("%s (%s)"), *A->GetActorLabel(), *A->GetClass()->GetName()));
	}

	OutResult = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> Arr;
	for (auto& S : Missing) Arr.Add(MakeShared<FJsonValueString>(S));
	OutResult->SetArrayField(TEXT("ActorsWithMissingRefs"), Arr);
	OutResult->SetNumberField(TEXT("count"), Missing.Num());
	OutResult->SetStringField(TEXT("message"),
		Missing.Num() > 0
		? FString::Printf(TEXT("Found %d actors with missing references"), Missing.Num())
		: TEXT("No missing references found"));
	return true;
}

bool UASceneAnalysisCommands::FindDuplicateNames(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) { OutError = TEXT("No world available"); return false; }

	TMap<FString, int32> NameCount;
	for (TActorIterator<AActor> It(World); It; ++It)
		if (IsValid(*It))
			NameCount.FindOrAdd((*It)->GetActorLabel())++;

	TArray<FString> Dupes;
	for (const auto& P : NameCount)
		if (P.Value > 1)
			Dupes.Add(FString::Printf(TEXT("'%s': %d instances"), *P.Key, P.Value));

	OutResult = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> Arr;
	for (auto& S : Dupes) Arr.Add(MakeShared<FJsonValueString>(S));
	OutResult->SetArrayField(TEXT("DuplicateNames"), Arr);
	OutResult->SetNumberField(TEXT("count"), Dupes.Num());
	OutResult->SetStringField(TEXT("message"),
		Dupes.Num() > 0
		? FString::Printf(TEXT("Found %d duplicate names"), Dupes.Num())
		: TEXT("No duplicate names found"));
	return true;
}

bool UASceneAnalysisCommands::FindOversizedMeshes(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) { OutError = TEXT("No world available"); return false; }

	int32 Threshold = Params->HasField(TEXT("VertexThreshold"))
		? (int32)Params->GetNumberField(TEXT("VertexThreshold")) : 50000;

	TArray<FString> Found;
	for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
	{
		AStaticMeshActor* A = *It;
		if (!IsValid(A)) continue;
		if (UStaticMeshComponent* MC = A->GetStaticMeshComponent())
			if (UStaticMesh* SM = MC->GetStaticMesh())
				if (SM->GetRenderData())
				{
					int64 Verts = 0;
					if (SM->GetRenderData()->LODResources.Num() > 0)
						Verts = SM->GetRenderData()->LODResources[0].GetNumVertices();
					if (Verts > Threshold)
						Found.Add(FString::Printf(TEXT("%s: %lld verts (%s)"), *A->GetActorLabel(), Verts, *SM->GetName()));
				}
	}

	OutResult = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> Arr;
	for (auto& S : Found) Arr.Add(MakeShared<FJsonValueString>(S));
	OutResult->SetArrayField(TEXT("OversizedMeshes"), Arr);
	OutResult->SetNumberField(TEXT("count"), Found.Num());
	OutResult->SetNumberField(TEXT("threshold"), Threshold);
	OutResult->SetStringField(TEXT("message"),
		Found.Num() > 0
		? FString::Printf(TEXT("Found %d oversized meshes (threshold: %d)"), Found.Num(), Threshold)
		: FString::Printf(TEXT("No oversized meshes found (threshold: %d)"), Threshold));
	return true;
}

bool UASceneAnalysisCommands::ValidateLevel(
	const TSharedPtr<FJsonObject>& Params,
	TSharedPtr<FJsonObject>& OutResult,
	FString& OutError)
{
	UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!World) { OutError = TEXT("No world available"); return false; }

	TArray<FString> Issues;
	int32 Checked = 0;

	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (!IsValid(Actor)) continue;
		Checked++;

		if (AStaticMeshActor* SMA = Cast<AStaticMeshActor>(Actor))
			if (UStaticMeshComponent* MC = SMA->GetStaticMeshComponent())
			{
				if (MC->GetCollisionEnabled() == ECollisionEnabled::NoCollision)
					Issues.Add(FString::Printf(TEXT("[No Collision] %s"), *Actor->GetActorLabel()));
				if (UStaticMesh* SM = MC->GetStaticMesh())
					if (MC->Mobility == EComponentMobility::Movable &&
						SM->GetRenderData() &&
						SM->GetRenderData()->LODResources[0].GetNumVertices() > 10000)
						Issues.Add(FString::Printf(TEXT("[High-Poly Movable] %s"), *Actor->GetActorLabel()));
			}

		if (ALight* LA = Cast<ALight>(Actor))
			if (ULightComponent* LC = LA->GetLightComponent())
				if (!LC->CastShadows)
					Issues.Add(FString::Printf(TEXT("[No Shadows] %s"), *Actor->GetActorLabel()));

		FVector Loc = Actor->GetActorLocation();
		const float MaxBounds = 1000000.0f;
		if (FMath::Abs(Loc.X) > MaxBounds || FMath::Abs(Loc.Y) > MaxBounds || FMath::Abs(Loc.Z) > MaxBounds)
			Issues.Add(FString::Printf(TEXT("[Out of Bounds] %s (%.0f, %.0f, %.0f)"), *Actor->GetActorLabel(), Loc.X, Loc.Y, Loc.Z));
	}

	OutResult = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> Arr;
	for (auto& S : Issues) Arr.Add(MakeShared<FJsonValueString>(S));
	OutResult->SetArrayField(TEXT("Issues"), Arr);
	OutResult->SetNumberField(TEXT("IssueCount"), Issues.Num());
	OutResult->SetNumberField(TEXT("TotalChecked"), Checked);
	OutResult->SetStringField(TEXT("message"),
		Issues.Num() > 0
		? FString::Printf(TEXT("Found %d issues (checked %d actors)"), Issues.Num(), Checked)
		: FString::Printf(TEXT("No issues found (checked %d actors)"), Checked));
	return true;
}