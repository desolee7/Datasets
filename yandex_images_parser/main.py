from utils import save_images, make_directory
from yandex_images_parser import Parser
import os

#               НАСТРОЙКИ 
QUERY = "разрушение кирпичной кладки наружных стен"
MAIN_IMAGES_LIMIT = 50   # сколько основных изображений
SIMILAR_LIMIT = 10   # сколько похожих на каждое



parser = Parser(headless=False)

print(f"Поиск: '{QUERY}'")

main_images = parser.query_search(
    query=QUERY,
    limit=MAIN_IMAGES_LIMIT,
    # size=parser.size.medium,
    # orientation=parser.orientation.square
)

print(f"Найдено основных изображений: {len(main_images)}")

base_dir = f"./Spalling (Разрушение поверхности)/{QUERY.replace(' ', '_')}" # имя корневой папки
make_directory(base_dir)
print(f"Основная папка: {base_dir}")

for idx, img_url in enumerate(main_images, 1):
    print(f"\n{'─'*40}")
    print(f"Папка {idx}/{len(main_images)}")
    
    folder_path = os.path.join(base_dir, str(idx))
    make_directory(folder_path)
    
    save_images([img_url], dir_path=folder_path, prefix="original", number_images=False)
    
    try:
        similar = parser.image_search(url=img_url, limit=SIMILAR_LIMIT)
        
        if similar:
            save_images(similar, dir_path=folder_path, prefix="similar", number_images=True)
            print(f"Сохранено {len(similar)} похожих")
        else:
            print(f"Похожие не найдены")
            
    except Exception as e:
        print(f"Ошибка: {e}")


print(f"\n{'='*50}")
print(f"Сохранено в {base_dir}")
print(f"Папок создано: {len(main_images)}")