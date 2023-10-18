import json
from datetime import datetime
import requests

access_token = '<Введите токен VK>'


class VK:

    def __init__(self, access_token_vk, user_id_vk, version='5.131'):
        self.token = access_token_vk
        self.id = user_id_vk
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    # Получаем информацию о пользователе
    def users_info(self):
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': self.id}
        response_user_info = requests.get(url, params={**self.params, **params})
        return response_user_info.json()

    # Получаем список всех альбомов пользователя, в словарь номер: id, title, size
    def get_albums(self):
        album_info_list = {}
        url = 'https://api.vk.com/method/photos.getAlbums'
        params = {'owner_id': self.users_info()['response'][0]['id'],  # Заменяем ник пользователя на id
                  'need_system': 1}
        response_get_albums = requests.get(url, params={**self.params, **params})
        try:
            for album_num, album in enumerate(response_get_albums.json()['response']['items']):
                album_info_list[str(album_num + 1)] = album['id'], album['title'], album['size']

            return album_info_list

        except Exception:
            return response_get_albums.json()['error']['error_msg']

    # Получаем список фотографий в альбоме - лайки, дата, имя файла(если лайти и дата одинаковые), ссылка
    def get_photos(self, album_id, count=5):
        photos_in_album_list = []
        url = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': self.users_info()['response'][0]['id'],
                  'album_id': album_id,
                  'extended': 1,
                  'count': count,
                  'offset': 0}

        try:
            while True:
                response_get_album_photos = requests.get(url, params={**self.params, **params})
                photos_in_album = response_get_album_photos.json()['response']['items']

                for photo in photos_in_album:
                    photo['date'] = datetime.fromtimestamp(photo['date']).strftime('%d-%m-%Y')
                    photos_in_album_list.append([
                        photo['likes']['count'] + photo['likes']['user_likes'],
                        photo['date'],
                        photo['sizes'][-1]['url'].split('/')[-1].split('?')[0],
                        photo['sizes'][-1]['url']
                    ])
                # Максимальное значение count - 1000, если фото больше - увеличиваем offset
                if len(photos_in_album) < 1000:
                    break

                params['offset'] += 1000

            return photos_in_album_list
        except Exception:
            return response_get_album_photos.json()['error']['error_msg']


class UserInterfaice:
    # Поиск пользователя
    def enter_user_name(self):
        while True:
            user_id = input('Введите ID или nickname: ')
            self.vk = VK(access_token, user_id)
            if self.vk.users_info()['response']:
                print(f'Приветствую, {self.vk.users_info()["response"][0]["first_name"]}!')
                print('Продолжим?')
                answer = input('Да/Нет: ').lower()
                if answer == 'да':

                    break
                else:
                    print('Попробуйте ещё раз.')
            else:
                print('Пользователь не найден')

        return self.vk

    # Выбор альбома
    def choose_album(self):
        user_albums = self.vk.get_albums()
        while True:
            for album in user_albums.items():
                print(f'{album[0]}. {album[1][1]} - {album[1][2]} фото.')

            try:
                album_id = input('Выберите альбом: ')
                if album_id in user_albums:
                    print(f'Вы выбрали альбом: {user_albums[album_id][1]}.')
                    print('Верно?')
                    answer = input('Да/Нет: ').lower()
                    if answer == 'да':
                        print('Ура')
                        self.photo_count = input('Укажите количество фото: ')
                        if self.photo_count == '':
                            self.photo_count = 5
                        break

                    else:
                        print('Попробуте ещё раз.')
                else:
                    print('Альбом не найден.')
            except ValueError:
                print('Неверный ввод.')

        return user_albums[album_id]

    # Выбор фото для загрузки
    def choose_photo(self):

        choosed_album = self.choose_album()
        photos_in_album = {choosed_album[1]: self.vk.get_photos(choosed_album[0], int(self.photo_count))}

        return photos_in_album


class YaDisk:
    # Создание папки
    def upload_files(self):
        self.user = UserInterfaice()
        self.user.enter_user_name()
        # Запрос токена и проверка
        while True:
            try:
                self.token = input('Введите токен Яндекс Диска: ')
                headers = {'Authorization': f'OAuth {self.token}'}
                response = requests.get('https://cloud-api.yandex.net/v1/disk/', headers=headers)

                if response.status_code != 200:
                    print('Токен неверный.')
                    continue
                else:
                    print(
                        f'Пользователь: {response.json()['user']['display_name']}.\n'
                        f'Всего места: {response.json()['total_space'] / 1024 ** 3} Гб. '
                        f'Доступно места: {(response.json()['total_space'] / 1024 ** 3) -
                                           (response.json()['used_space'] / 1024 ** 3)} Гб')
                    break
            except Exception:
                print('Токен неверный.')

        photo_to_upload = self.user.choose_photo()
        params = {'path': list(photo_to_upload.keys())}
        headers = {'Authorization': f'OAuth {self.token}'}
        response_create_directory = requests.put('https://cloud-api.yandex.net/v1/disk/resources/',
                                                 params=params,
                                                 headers=headers)
        # Проверка наличия папки
        if 'error' in response_create_directory.json():
            print('Папка уже существует. Приступаю к загрузке фалов...')
            pass
        else:
            print('Папка создана. Приступаю к загрузке фалов...')

        json_data = []
        files_count = len(list(photo_to_upload.values())[0])
        for photo in list(photo_to_upload.values())[0]:
            photo_name = f'{photo[0]} {photo[1]} {photo[2]}'
            params = {'url': photo[-1], 'path': f'{list(photo_to_upload.keys())[0]}/{photo_name}', }
            headers = {'Authorization': f'OAuth {self.token}'}
            # Проверка наличия файла
            check_files = requests.get(f'https://cloud-api.yandex.net/v1/disk/resources?path={params['path']}',
                                       headers=headers)
            if check_files.status_code == 200:

                print(f'Файл {photo_name} уже существует.')
                files_count -= 1
                print(f'Осталось {files_count} из {len(list(photo_to_upload.values())[0])} файлов.')

            else:
                response_file_size = requests.head(params['url'])
                file_size = int(
                    response_file_size.headers.get('Content-Length', 0)) / 1024 ** 2  # Получаем размер файла

                requests.post('https://cloud-api.yandex.net/v1/disk/resources/upload',
                              params=params, headers=headers)

                files_count -= 1
                print(f'Файл {photo_name} загружен. {file_size:.2f} Мб')
                print(f'Осталось {files_count} из {len(list(photo_to_upload.values())[0])} файлов')

                json_data.append({'file_name': photo_name, 'size': f'{file_size:.2f} Мб'})

        with open('data.json', 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)

        with open('data.json', 'r', encoding='utf-8') as json_file:
            print(json_file.read())


if __name__ == '__main__':
    yadisk = YaDisk()
    yadisk.upload_files()
