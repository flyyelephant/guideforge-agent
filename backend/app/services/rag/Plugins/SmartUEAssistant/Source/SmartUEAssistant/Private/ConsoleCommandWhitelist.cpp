// Copyright Epic Games, Inc. All Rights Reserved.

#include "ConsoleCommandWhitelist.h"
#include "SmartUEAssistantLog.h"

// 静态成员初始化
// Static member initialization
TSet<FString> FConsoleCommandWhitelist::AllowedPrefixes;
TSet<FString> FConsoleCommandWhitelist::BlockedCommands;
bool FConsoleCommandWhitelist::bInitialized = false;
FCriticalSection FConsoleCommandWhitelist::AccessLock;

void FConsoleCommandWhitelist::InitializeDefaults()
{
	if (bInitialized)
	{
		return;
	}
	
	FScopeLock Lock(&AccessLock);
	
	// 获取锁后再次检查（双重检查锁定模式）
	// Double-check after acquiring lock
	if (bInitialized)
	{
		return;
	}
	
	// ===== 允许的命令前缀 / Allowed command prefixes =====
	
	// 视口和渲染 / Viewport and rendering
	AllowedPrefixes.Add(TEXT("show"));        // show collision, show bounds, etc.
	AllowedPrefixes.Add(TEXT("viewmode"));    // viewmode lit, wireframe, etc.
	AllowedPrefixes.Add(TEXT("r."));          // 渲染变量 / rendering CVars (r.ScreenPercentage, etc.)
	
	// 统计和性能分析 / Statistics and profiling
	AllowedPrefixes.Add(TEXT("stat"));        // stat fps, stat unit, etc.
	AllowedPrefixes.Add(TEXT("profile"));     // 性能分析命令 / profiling commands
	
	// 调试可视化 / Debugging visualization
	AllowedPrefixes.Add(TEXT("showdebug"));   // showdebug ai, showdebug collision
	AllowedPrefixes.Add(TEXT("displayall"));  // 显示所有变量 / display all variables
	AllowedPrefixes.Add(TEXT("getall"));      // 获取所有对象属性 / get all object properties
	
	// 安全的控制台变量 / Safe console variables
	AllowedPrefixes.Add(TEXT("t."));          // 时间变量 / time CVars
	AllowedPrefixes.Add(TEXT("a."));          // 动画变量 / animation CVars
	AllowedPrefixes.Add(TEXT("p."));          // 物理变量 / physics CVars
	AllowedPrefixes.Add(TEXT("fx."));         // 特效变量 / effects CVars
	AllowedPrefixes.Add(TEXT("foliage."));    // 植被变量 / foliage CVars
	AllowedPrefixes.Add(TEXT("grass."));      // 草地变量 / grass CVars
	
	// 关卡流送 / Level streaming
	AllowedPrefixes.Add(TEXT("streamlevel")); // 流送关卡 / stream level in/out
	
	// 安全的游戏命令 / Safe gameplay commands
	AllowedPrefixes.Add(TEXT("teleport"));    // 传送玩家 / teleport player
	AllowedPrefixes.Add(TEXT("god"));         // 上帝模式（编辑器中安全）/ god mode (safe in editor)
	AllowedPrefixes.Add(TEXT("ghost"));       // 幽灵模式 / ghost mode
	AllowedPrefixes.Add(TEXT("walk"));        // 行走模式 / walk mode
	AllowedPrefixes.Add(TEXT("fly"));         // 飞行模式 / fly mode
	
	// 相机 / Camera
	AllowedPrefixes.Add(TEXT("camera"));      // 相机命令 / camera commands
	AllowedPrefixes.Add(TEXT("fov"));         // 视野 / field of view
	
	// ===== 阻止的命令 / Blocked commands =====
	
	// 编辑器控制 / Editor control
	BlockedCommands.Add(TEXT("exit"));
	BlockedCommands.Add(TEXT("quit"));
	BlockedCommands.Add(TEXT("closeeditor"));
	
	// 文件操作 / File operations
	BlockedCommands.Add(TEXT("savemap"));
	BlockedCommands.Add(TEXT("saveall"));
	BlockedCommands.Add(TEXT("deletefile"));
	BlockedCommands.Add(TEXT("renamefile"));
	BlockedCommands.Add(TEXT("movefile"));
	
	// 资产操作 / Asset operations
	BlockedCommands.Add(TEXT("deleteasset"));
	BlockedCommands.Add(TEXT("renameasset"));
	BlockedCommands.Add(TEXT("obj delete"));
	
	// 进程控制 / Process control
	BlockedCommands.Add(TEXT("exec"));        // 执行脚本文件 / execute script file
	BlockedCommands.Add(TEXT("open"));        // 打开外部文件/URL / open external file/url
	BlockedCommands.Add(TEXT("start"));       // 启动进程 / start process
	
	// 危险的游戏操作 / Dangerous gameplay
	BlockedCommands.Add(TEXT("destroyall"));
	BlockedCommands.Add(TEXT("killall"));
	BlockedCommands.Add(TEXT("removeall"));
	
	// 网络/服务器（潜在危险）/ Network/Server (potentially dangerous)
	BlockedCommands.Add(TEXT("disconnect"));
	BlockedCommands.Add(TEXT("servertravel"));
	
	// 内存操作 / Memory operations
	BlockedCommands.Add(TEXT("memreport"));   // 可能很慢/冻结 / can be slow/freeze
	BlockedCommands.Add(TEXT("obj gc"));      // 垃圾回收 / garbage collection
	
	bInitialized = true;
	
	UE_LOG(LogSmartUEAssistant, Log, 
		TEXT("ConsoleCommandWhitelist initialized: %d allowed prefixes, %d blocked commands"),
		AllowedPrefixes.Num(), BlockedCommands.Num());
}

void FConsoleCommandWhitelist::EnsureInitialized()
{
	if (!bInitialized)
	{
		InitializeDefaults();
	}
}

FString FConsoleCommandWhitelist::ExtractBaseCommand(const FString& FullCommand)
{
	// Trim whitespace
	FString Trimmed = FullCommand.TrimStartAndEnd();
	
	// Extract first word (command name)
	int32 SpaceIndex;
	if (Trimmed.FindChar(TEXT(' '), SpaceIndex))
	{
		return Trimmed.Left(SpaceIndex);
	}
	
	return Trimmed;
}

bool FConsoleCommandWhitelist::HasAllowedPrefix(const FString& Command)
{
	FString LowerCommand = Command.ToLower();
	
	for (const FString& Prefix : AllowedPrefixes)
	{
		if (LowerCommand.StartsWith(Prefix.ToLower()))
		{
			return true;
		}
	}
	
	return false;
}

bool FConsoleCommandWhitelist::IsBlocked(const FString& Command)
{
	FString BaseCommand = ExtractBaseCommand(Command);
	FString LowerBase = BaseCommand.ToLower();
	
	for (const FString& Blocked : BlockedCommands)
	{
		if (LowerBase.Equals(Blocked.ToLower()))
		{
			return true;
		}
	}
	
	return false;
}

bool FConsoleCommandWhitelist::IsCommandSafe(const FString& Command)
{
	EnsureInitialized();
	
	FScopeLock Lock(&AccessLock);
	
	// Empty command is not safe
	if (Command.IsEmpty())
	{
		return false;
	}
	
	// Check if explicitly blocked first
	if (IsBlocked(Command))
	{
		UE_LOG(LogSmartUEAssistant, Warning, 
			TEXT("Command blocked (explicit): %s"), *Command);
		return false;
	}
	
	// Check if has allowed prefix
	if (HasAllowedPrefix(Command))
	{
		UE_LOG(LogSmartUEAssistant, Verbose, 
			TEXT("Command allowed (prefix match): %s"), *Command);
		return true;
	}
	
	// Not in whitelist
	UE_LOG(LogSmartUEAssistant, Warning, 
		TEXT("Command blocked (not whitelisted): %s"), *Command);
	return false;
}

TArray<FString> FConsoleCommandWhitelist::GetAllowedPrefixes()
{
	EnsureInitialized();
	FScopeLock Lock(&AccessLock);
	
	return AllowedPrefixes.Array();
}

TArray<FString> FConsoleCommandWhitelist::GetBlockedCommands()
{
	EnsureInitialized();
	FScopeLock Lock(&AccessLock);
	
	return BlockedCommands.Array();
}

void FConsoleCommandWhitelist::AddAllowedPrefix(const FString& Prefix)
{
	EnsureInitialized();
	FScopeLock Lock(&AccessLock);
	
	AllowedPrefixes.Add(Prefix);
	
	UE_LOG(LogSmartUEAssistant, Log, 
		TEXT("Added allowed command prefix: %s"), *Prefix);
}

void FConsoleCommandWhitelist::AddBlockedCommand(const FString& Command)
{
	EnsureInitialized();
	FScopeLock Lock(&AccessLock);
	
	BlockedCommands.Add(Command);
	
	UE_LOG(LogSmartUEAssistant, Log, 
		TEXT("Added blocked command: %s"), *Command);
}

FString FConsoleCommandWhitelist::GetBlockReason(const FString& Command)
{
	EnsureInitialized();
	
	if (Command.IsEmpty())
	{
		return TEXT("空命令不允许执行");
	}
	
	if (IsBlocked(Command))
	{
		return FString::Printf(
			TEXT("命令 '%s' 在黑名单中，可能导致数据丢失或编辑器崩溃"),
			*ExtractBaseCommand(Command));
	}
	
	if (!HasAllowedPrefix(Command))
	{
		return FString::Printf(
			TEXT("命令 '%s' 不在白名单中。允许的命令前缀：%s"),
			*ExtractBaseCommand(Command),
			*FString::Join(GetAllowedPrefixes(), TEXT(", ")));
	}
	
	return TEXT("命令通过安全检查");
}

