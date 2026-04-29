// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "FSceneContext.generated.h"

/**
 * 编辑器操作的场景上下文数据模型
 * Scene context data model for editor operations
 * 
 * 此数据模型提供关卡信息、选中对象、视口相机和其他上下文数据的统一描述。
 * 可以序列化并注入到 AI 提示词中。
 * 
 * This data model provides a unified description of level information, selected objects,
 * viewport camera, and other contextual data. It can be serialized and injected into AI prompts.
 */

/**
 * 场景中 Actor 的简要摘要
 * Brief summary of an actor in the scene
 */
USTRUCT(BlueprintType)
struct SMARTUEASSISTANT_API FSceneActorBrief
{
	GENERATED_BODY()

	/** 场景中的 Actor 名称 / Actor name in the scene */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FString Name;

	/** Actor 类名 / Actor class name */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FString Class;

	/** 世界位置 / World location */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FVector Location = FVector::ZeroVector;

	/** 世界旋转 / World rotation */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FRotator Rotation = FRotator::ZeroRotator;

	/** 世界缩放 / World scale */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FVector Scale = FVector(1, 1, 1);

	/** 组件数量（可选，由设置控制）/ Number of components (optional, controlled by settings) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	int32 ComponentCount = 0;
};

/**
 * 关卡及其 Actor 的简要摘要
 * Brief summary of a level and its actors
 */
USTRUCT(BlueprintType)
struct SMARTUEASSISTANT_API FSceneLevelBrief
{
	GENERATED_BODY()

	/** 关卡名称 / Level name */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FString LevelName;

	/** 此关卡中的 Actor / Actors in this level */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	TArray<FSceneActorBrief> Actors;
};

/**
 * 场景统计信息
 * Scene statistics
 */
USTRUCT(BlueprintType)
struct SMARTUEASSISTANT_API FSceneStats
{
	GENERATED_BODY()

	/** 已加载的关卡数量 / Number of loaded levels */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	int32 Levels = 0;

	/** 已选择的 Actor 数量 / Number of selected actors */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	int32 SelectedCount = 0;

	/** 场景中的 Actor 总数 / Total number of actors in scene */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	int32 ActorCount = 0;

	/** Top-N Actor 类计数 / Top-N actor class counts */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	TMap<FString, int32> ClassCounts;
};

/**
 * 完整的场景上下文信息
 * Complete scene context information
 * 
 * 包含用于 AI 上下文注入的所有相关场景数据：
 * Contains all relevant scene data for AI context injection:
 * - 关卡层次结构和 Actor / Level hierarchy and actors
 * - 已选择的 Actor / Selected actors
 * - 视口相机位置 / Viewport camera position
 * - 场景统计信息 / Scene statistics
 */
USTRUCT(BlueprintType)
struct SMARTUEASSISTANT_API FSceneContext
{
	GENERATED_BODY()

	/** 世界类型（例如 "Editor"、"PIE"）/ World type (e.g., "Editor", "PIE") */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FString WorldType = TEXT("Editor");

	/** 所有已加载的关卡及其 Actor / All loaded levels and their actors */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	TArray<FSceneLevelBrief> Levels;

	/** 当前选中的 Actor / Currently selected actors */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	TArray<FSceneActorBrief> Selected;

	/** 视口相机位置（可选，由设置控制）/ Viewport camera location (optional, controlled by settings) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FVector ViewLocation = FVector::ZeroVector;

	/** 视口相机旋转（可选，由设置控制）/ Viewport camera rotation (optional, controlled by settings) */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FRotator ViewRotation = FRotator::ZeroRotator;

	/** 场景统计信息 / Scene statistics */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Scene")
	FSceneStats Stats;
};