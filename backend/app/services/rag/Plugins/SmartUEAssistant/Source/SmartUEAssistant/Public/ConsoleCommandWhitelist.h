// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * AI 执行控制台命令的安全白名单
 * Console command whitelist for safe AI execution
 * 
 * 将 AI 执行的控制台命令限制在安全子集内。
 * 防止潜在的危险操作，如文件删除、进程终止或编辑器关闭。
 * 
 * Restricts AI-executed console commands to a safe subset.
 * Prevents potentially dangerous operations like file deletion,
 * process termination, or editor shutdown.
 */
class SMARTUEASSISTANT_API FConsoleCommandWhitelist
{
public:
	/**
	 * 检查命令是否安全可执行
	 * Check if a command is safe to execute
	 * 
	 * @param Command 要验证的完整命令字符串 / Full command string to validate
	 * @return 如果命令在白名单中且安全则返回 true / True if command is whitelisted and safe
	 */
	static bool IsCommandSafe(const FString& Command);
	
	/**
	 * 获取所有允许的命令前缀列表
	 * Get list of all allowed command prefixes
	 * 
	 * @return 安全命令前缀数组 / Array of safe command prefixes
	 */
	static TArray<FString> GetAllowedPrefixes();
	
	/**
	 * 获取被阻止的命令列表
	 * Get list of blocked commands
	 * 
	 * @return 危险命令名称数组 / Array of dangerous command names
	 */
	static TArray<FString> GetBlockedCommands();
	
	/**
	 * 运行时添加自定义允许的前缀
	 * Add a custom allowed prefix at runtime
	 * 
	 * @param Prefix 要允许的命令前缀 / Command prefix to allow
	 */
	static void AddAllowedPrefix(const FString& Prefix);
	
	/**
	 * 运行时添加自定义阻止的命令
	 * Add a custom blocked command at runtime
	 * 
	 * @param Command 要阻止的命令 / Command to block
	 */
	static void AddBlockedCommand(const FString& Command);
	
	/**
	 * 获取命令被阻止的详细原因
	 * Get detailed reason why a command was blocked
	 * 
	 * @param Command 被检查的命令 / Command that was checked
	 * @return 人类可读的原因 / Human-readable reason
	 */
	static FString GetBlockReason(const FString& Command);

private:
	/** 初始化默认白名单和黑名单 / Initialize default whitelist and blacklist */
	static void InitializeDefaults();
	
	/** 允许的命令前缀（不区分大小写）/ Allowed command prefixes (case-insensitive) */
	static TSet<FString> AllowedPrefixes;
	
	/** 明确阻止的命令（不区分大小写）/ Explicitly blocked commands (case-insensitive) */
	static TSet<FString> BlockedCommands;
	
	/** 是否已初始化默认值 / Whether defaults have been initialized */
	static bool bInitialized;
	
	/** 线程安全访问锁 / Thread-safe access */
	static FCriticalSection AccessLock;
	
	/** 确保已初始化 / Ensure initialization has occurred */
	static void EnsureInitialized();
	
	/** 检查命令是否以允许的前缀开头 / Check if command starts with any allowed prefix */
	static bool HasAllowedPrefix(const FString& Command);
	
	/** 检查命令是否被明确阻止 / Check if command is explicitly blocked */
	static bool IsBlocked(const FString& Command);
	
	/** 从完整命令字符串中提取基础命令 / Extract base command from full command string */
	static FString ExtractBaseCommand(const FString& FullCommand);
};

