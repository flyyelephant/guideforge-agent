using UnrealBuildTool;

public class SmartUEAssistant : ModuleRules
{
	public SmartUEAssistant(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;
		
		// 公共依赖模块
		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
				"InputCore",
				"Slate",
				"SlateCore",
				"ToolWidgets",
				"EditorWidgets",
				"HTTP",
				"Json",
				"JsonUtilities"
			}
		);

		// 私有依赖模块（仅编辑器模式）
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(
				new string[]
				{
					"UnrealEd",
					"EditorStyle",
					"ToolMenus",
					"Projects",
					"LevelEditor",
					"Settings" // 新增：用于注册项目设置页
					"UnrealAgent"
				}
			);
		}
	}
}