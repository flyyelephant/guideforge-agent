// Copyright KuoYu. All Rights Reserved.
// Migrated from SmartUEAssistant

#include "UAPropertyModificationHelper.h"
#include "UnrealAgent.h"
#include "Editor.h"
#include "GameFramework/Actor.h"
#include "Components/ActorComponent.h"
#include "Components/LightComponent.h"
#include "Components/SceneComponent.h"
#include "UObject/UnrealType.h"
#include "Dom/JsonObject.h"

bool FUAPropertyModificationHelper::ParseColor(const TSharedPtr<FJsonValue>& Value, FLinearColor& OutColor)
{
	if (!Value.IsValid()) return false;

	if (Value->Type == EJson::Object)
	{
		const TSharedPtr<FJsonObject>& Obj = Value->AsObject();
		if (Obj->HasField(TEXT("R")) && Obj->HasField(TEXT("G")) && Obj->HasField(TEXT("B")))
		{
			OutColor.R = Obj->GetNumberField(TEXT("R"));
			OutColor.G = Obj->GetNumberField(TEXT("G"));
			OutColor.B = Obj->GetNumberField(TEXT("B"));
			OutColor.A = Obj->HasField(TEXT("A")) ? Obj->GetNumberField(TEXT("A")) : 1.0f;
			return true;
		}
	}
	else if (Value->Type == EJson::String)
	{
		FString ColorName = Value->AsString().ToLower();
		if (ColorName == TEXT("red"))         OutColor = FLinearColor::Red;
		else if (ColorName == TEXT("green"))  OutColor = FLinearColor::Green;
		else if (ColorName == TEXT("blue"))   OutColor = FLinearColor::Blue;
		else if (ColorName == TEXT("white"))  OutColor = FLinearColor::White;
		else if (ColorName == TEXT("black"))  OutColor = FLinearColor::Black;
		else if (ColorName == TEXT("yellow")) OutColor = FLinearColor::Yellow;
		else if (ColorName == TEXT("cyan"))   OutColor = FLinearColor(0, 1, 1);
		else if (ColorName == TEXT("magenta"))OutColor = FLinearColor(1, 0, 1);
		else if (ColorName == TEXT("orange")) OutColor = FLinearColor(1, 0.5f, 0);
		else if (ColorName == TEXT("purple")) OutColor = FLinearColor(0.5f, 0, 1);
		else if (ColorName == TEXT("pink"))   OutColor = FLinearColor(1, 0.5f, 0.5f);
		else if (ColorName == TEXT("brown"))  OutColor = FLinearColor(0.6f, 0.3f, 0.0f);
		else if (ColorName == TEXT("gray") || ColorName == TEXT("grey")) OutColor = FLinearColor(0.5f, 0.5f, 0.5f);
		else return false;
		return true;
	}
	return false;
}

bool FUAPropertyModificationHelper::ParseVector(const TSharedPtr<FJsonValue>& Value, FVector& OutVector)
{
	if (!Value.IsValid() || Value->Type != EJson::Object) return false;
	const TSharedPtr<FJsonObject>& Obj = Value->AsObject();
	if (Obj->HasField(TEXT("X")) && Obj->HasField(TEXT("Y")) && Obj->HasField(TEXT("Z")))
	{
		OutVector.X = Obj->GetNumberField(TEXT("X"));
		OutVector.Y = Obj->GetNumberField(TEXT("Y"));
		OutVector.Z = Obj->GetNumberField(TEXT("Z"));
		return true;
	}
	return false;
}

bool FUAPropertyModificationHelper::ParseRotator(const TSharedPtr<FJsonValue>& Value, FRotator& OutRotator)
{
	if (!Value.IsValid() || Value->Type != EJson::Object) return false;
	const TSharedPtr<FJsonObject>& Obj = Value->AsObject();
	if (Obj->HasField(TEXT("Pitch")) && Obj->HasField(TEXT("Yaw")) && Obj->HasField(TEXT("Roll")))
	{
		OutRotator.Pitch = Obj->GetNumberField(TEXT("Pitch"));
		OutRotator.Yaw   = Obj->GetNumberField(TEXT("Yaw"));
		OutRotator.Roll  = Obj->GetNumberField(TEXT("Roll"));
		return true;
	}
	return false;
}

FProperty* FUAPropertyModificationHelper::FindPropertyByPath(UObject* Object, const FString& PropertyPath, UObject*& OutContainer)
{
	if (!Object || PropertyPath.IsEmpty()) return nullptr;

	TArray<FString> PathParts;
	PropertyPath.ParseIntoArray(PathParts, TEXT("."));

	OutContainer = Object;
	FProperty* Property = nullptr;

	for (int32 i = 0; i < PathParts.Num(); ++i)
	{
		const FString& PartName = PathParts[i];
		Property = FindFProperty<FProperty>(OutContainer->GetClass(), *PartName);

		if (!Property && i < PathParts.Num() - 1)
		{
			if (AActor* Actor = Cast<AActor>(OutContainer))
			{
				TArray<UActorComponent*> Components;
				Actor->GetComponents(Components);
				for (UActorComponent* Component : Components)
				{
					if (Component &&
						(Component->GetName().Equals(PartName, ESearchCase::IgnoreCase) ||
						 Component->GetClass()->GetName().Contains(PartName)))
					{
						OutContainer = Component;
						break;
					}
				}
			}
			continue;
		}

		if (!Property) return nullptr;

		if (i < PathParts.Num() - 1)
		{
			if (FObjectProperty* ObjProp = CastField<FObjectProperty>(Property))
			{
				UObject* NextContainer = ObjProp->GetObjectPropertyValue(Property->ContainerPtrToValuePtr<void>(OutContainer));
				if (!NextContainer) return nullptr;
				OutContainer = NextContainer;
			}
			else
			{
				return nullptr;
			}
		}
	}
	return Property;
}

bool FUAPropertyModificationHelper::SetPropertyValueDirect(
	FProperty* Property,
	void* ContainerPtr,
	const TSharedPtr<FJsonValue>& Value,
	FString& OutError)
{
	if (!Property || !ContainerPtr || !Value.IsValid())
	{
		OutError = TEXT("Invalid parameters");
		return false;
	}

	void* ValuePtr = Property->ContainerPtrToValuePtr<void>(ContainerPtr);

	if (FFloatProperty* FloatP = CastField<FFloatProperty>(Property))
	{
		if (Value->Type == EJson::Number) { FloatP->SetPropertyValue(ValuePtr, (float)Value->AsNumber()); return true; }
	}
	else if (FDoubleProperty* DoubleP = CastField<FDoubleProperty>(Property))
	{
		if (Value->Type == EJson::Number) { DoubleP->SetPropertyValue(ValuePtr, Value->AsNumber()); return true; }
	}
	else if (FIntProperty* IntP = CastField<FIntProperty>(Property))
	{
		if (Value->Type == EJson::Number) { IntP->SetPropertyValue(ValuePtr, (int32)Value->AsNumber()); return true; }
	}
	else if (FBoolProperty* BoolP = CastField<FBoolProperty>(Property))
	{
		if (Value->Type == EJson::Boolean) { BoolP->SetPropertyValue(ValuePtr, Value->AsBool()); return true; }
	}
	else if (FStrProperty* StrP = CastField<FStrProperty>(Property))
	{
		if (Value->Type == EJson::String) { StrP->SetPropertyValue(ValuePtr, Value->AsString()); return true; }
	}
	else if (FNameProperty* NameP = CastField<FNameProperty>(Property))
	{
		if (Value->Type == EJson::String) { NameP->SetPropertyValue(ValuePtr, FName(*Value->AsString())); return true; }
	}
	else if (FTextProperty* TextP = CastField<FTextProperty>(Property))
	{
		if (Value->Type == EJson::String) { TextP->SetPropertyValue(ValuePtr, FText::FromString(Value->AsString())); return true; }
	}
	else if (FStructProperty* StructProp = CastField<FStructProperty>(Property))
	{
		FString StructName = StructProp->Struct->GetName();
		if (StructName == TEXT("Vector"))
		{
			FVector Vec;
			if (ParseVector(Value, Vec)) { *static_cast<FVector*>(ValuePtr) = Vec; return true; }
		}
		else if (StructName == TEXT("Rotator"))
		{
			FRotator Rot;
			if (ParseRotator(Value, Rot)) { *static_cast<FRotator*>(ValuePtr) = Rot; return true; }
		}
		else if (StructName == TEXT("LinearColor"))
		{
			FLinearColor Color;
			if (ParseColor(Value, Color)) { *static_cast<FLinearColor*>(ValuePtr) = Color; return true; }
		}
		else if (StructName == TEXT("Color"))
		{
			FLinearColor Color;
			if (ParseColor(Value, Color)) { *static_cast<FColor*>(ValuePtr) = Color.ToFColor(true); return true; }
		}
	}
	else if (FEnumProperty* EnumProp = CastField<FEnumProperty>(Property))
	{
		if (Value->Type == EJson::String)
		{
			int64 EnumValue = EnumProp->GetEnum()->GetValueByNameString(Value->AsString());
			if (EnumValue != INDEX_NONE) { EnumProp->GetUnderlyingProperty()->SetIntPropertyValue(ValuePtr, EnumValue); return true; }
		}
		else if (Value->Type == EJson::Number)
		{
			EnumProp->GetUnderlyingProperty()->SetIntPropertyValue(ValuePtr, (int64)Value->AsNumber());
			return true;
		}
	}
	else if (FByteProperty* ByteProp = CastField<FByteProperty>(Property))
	{
		if (ByteProp->Enum && Value->Type == EJson::String)
		{
			int64 EnumValue = ByteProp->Enum->GetValueByNameString(Value->AsString());
			if (EnumValue != INDEX_NONE) { ByteProp->SetPropertyValue(ValuePtr, (uint8)EnumValue); return true; }
		}
		if (Value->Type == EJson::Number) { ByteProp->SetPropertyValue(ValuePtr, (uint8)Value->AsNumber()); return true; }
	}

	OutError = FString::Printf(TEXT("Unsupported property type: %s"), *Property->GetClass()->GetName());
	return false;
}

bool FUAPropertyModificationHelper::SetPropertyValue(
	UObject* Object,
	const FString& PropertyPath,
	const TSharedPtr<FJsonValue>& Value,
	bool bCreateTransaction,
	const FString& TransactionDescription,
	FString& OutError)
{
	if (!Object)
	{
		OutError = TEXT("Invalid object");
		return false;
	}

	UObject* Container = nullptr;
	FProperty* Property = FindPropertyByPath(Object, PropertyPath, Container);

	if (!Property || !Container)
	{
		OutError = FString::Printf(TEXT("Property not found: %s on %s"), *PropertyPath, *Object->GetName());
		return false;
	}

	if (!IsPropertyEditable(Property))
	{
		OutError = FString::Printf(TEXT("Property is not editable: %s"), *PropertyPath);
		return false;
	}

	TOptional<FScopedTransaction> Transaction;
	if (bCreateTransaction)
	{
		Transaction.Emplace(FText::FromString(TransactionDescription));
	}

	Container->Modify();
	bool bSuccess = SetPropertyValueDirect(Property, Container, Value, OutError);

	if (bSuccess)
	{
		FPropertyChangedEvent PropertyChangedEvent(Property, EPropertyChangeType::ValueSet);
		Container->PostEditChangeProperty(PropertyChangedEvent);

		if (UActorComponent* Comp = Cast<UActorComponent>(Container))
			Comp->MarkRenderStateDirty();
		if (USceneComponent* SceneComp = Cast<USceneComponent>(Container))
			SceneComp->UpdateComponentToWorld();
	}
	else if (Transaction.IsSet())
	{
		Transaction->Cancel();
	}

	return bSuccess;
}

TSharedPtr<FJsonValue> FUAPropertyModificationHelper::GetPropertyValueAsJson(FProperty* Property, const void* ContainerPtr)
{
	if (!Property || !ContainerPtr) return nullptr;
	const void* ValuePtr = Property->ContainerPtrToValuePtr<const void>(ContainerPtr);

	if (FFloatProperty* P = CastField<FFloatProperty>(Property))
		return MakeShared<FJsonValueNumber>(P->GetPropertyValue(ValuePtr));
	if (FDoubleProperty* P = CastField<FDoubleProperty>(Property))
		return MakeShared<FJsonValueNumber>(P->GetPropertyValue(ValuePtr));
	if (FIntProperty* P = CastField<FIntProperty>(Property))
		return MakeShared<FJsonValueNumber>(P->GetPropertyValue(ValuePtr));
	if (FBoolProperty* P = CastField<FBoolProperty>(Property))
		return MakeShared<FJsonValueBoolean>(P->GetPropertyValue(ValuePtr));
	if (FStrProperty* P = CastField<FStrProperty>(Property))
		return MakeShared<FJsonValueString>(P->GetPropertyValue(ValuePtr));
	if (FNameProperty* P = CastField<FNameProperty>(Property))
		return MakeShared<FJsonValueString>(P->GetPropertyValue(ValuePtr).ToString());
	if (FTextProperty* P = CastField<FTextProperty>(Property))
		return MakeShared<FJsonValueString>(P->GetPropertyValue(ValuePtr).ToString());
	if (FStructProperty* StructProp = CastField<FStructProperty>(Property))
	{
		FString StructName = StructProp->Struct->GetName();
		if (StructName == TEXT("Vector"))
		{
			const FVector& V = *static_cast<const FVector*>(ValuePtr);
			TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
			Obj->SetNumberField(TEXT("X"), V.X);
			Obj->SetNumberField(TEXT("Y"), V.Y);
			Obj->SetNumberField(TEXT("Z"), V.Z);
			return MakeShared<FJsonValueObject>(Obj);
		}
		if (StructName == TEXT("Rotator"))
		{
			const FRotator& R = *static_cast<const FRotator*>(ValuePtr);
			TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
			Obj->SetNumberField(TEXT("Pitch"), R.Pitch);
			Obj->SetNumberField(TEXT("Yaw"), R.Yaw);
			Obj->SetNumberField(TEXT("Roll"), R.Roll);
			return MakeShared<FJsonValueObject>(Obj);
		}
		if (StructName == TEXT("LinearColor"))
		{
			const FLinearColor& C = *static_cast<const FLinearColor*>(ValuePtr);
			TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
			Obj->SetNumberField(TEXT("R"), C.R);
			Obj->SetNumberField(TEXT("G"), C.G);
			Obj->SetNumberField(TEXT("B"), C.B);
			Obj->SetNumberField(TEXT("A"), C.A);
			return MakeShared<FJsonValueObject>(Obj);
		}
	}
	return MakeShared<FJsonValueString>(TEXT("<unsupported type>"));
}

bool FUAPropertyModificationHelper::IsPropertyEditable(FProperty* Property)
{
	if (!Property) return false;
	return !Property->HasAnyPropertyFlags(CPF_BlueprintReadOnly | CPF_EditConst);
}

FString FUAPropertyModificationHelper::GetPropertyTypeName(FProperty* Property)
{
	if (!Property) return TEXT("Unknown");
	if (CastField<FFloatProperty>(Property))  return TEXT("Float");
	if (CastField<FDoubleProperty>(Property)) return TEXT("Double");
	if (CastField<FIntProperty>(Property))    return TEXT("Int");
	if (CastField<FBoolProperty>(Property))   return TEXT("Bool");
	if (CastField<FStrProperty>(Property))    return TEXT("String");
	if (CastField<FNameProperty>(Property))   return TEXT("Name");
	if (CastField<FTextProperty>(Property))   return TEXT("Text");
	if (FStructProperty* S = CastField<FStructProperty>(Property))
		return FString::Printf(TEXT("Struct<%s>"), *S->Struct->GetName());
	if (FEnumProperty* E = CastField<FEnumProperty>(Property))
		return FString::Printf(TEXT("Enum<%s>"), *E->GetEnum()->GetName());
	if (FObjectProperty* O = CastField<FObjectProperty>(Property))
		return FString::Printf(TEXT("Object<%s>"), *O->PropertyClass->GetName());
	return Property->GetClass()->GetName();
}