from energy.models import ResourceType, Meter, TariffComponent

def merge_resource_types(keep_id, remove_id):
    """
    Объединяет два типа ресурсов, переназначая все связанные объекты на keep_id
    и удаляя remove_id.
    """
    keep_type = ResourceType.objects.get(pk=keep_id)
    remove_type = ResourceType.objects.get(pk=remove_id)

    # Обновить компоненты тарифов
    updated_tariffs = TariffComponent.objects.filter(resource_type=remove_type).update(resource_type=keep_type)
    print(f"Обновлено компонентов тарифов: {updated_tariffs}")

    # Обновить счётчики
    updated_meters = Meter.objects.filter(resource_type=remove_type).update(resource_type=keep_type)
    print(f"Обновлено счётчиков: {updated_meters}")

    # Удалить дублирующий тип
    remove_type.delete()
    print("Тип ресурса удалён.")

if __name__ == "__main__":
    # Пример: объединить "Электроэнергия одноставочный" (id=2) в "Электроэнергия" (id=1)
    merge_resource_types(keep_id=2, remove_id=1)