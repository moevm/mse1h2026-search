import meilisearch
import os
from dotenv import load_dotenv

load_dotenv()

MEILI_URL = os.getenv('MEILI_URL', 'http://localhost:7700')
MEILI_MASTER_KEY = os.getenv('MEILI_MASTER_KEY', 'masterKey')

LANGUAGES = {
    'ru': {
        'locale_code': 'rus',
        'stop_words': [
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 
            'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 
            'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 
            'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 
            'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 
            'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 
            'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 
            'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 
            'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 
            'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 
            'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между'
        ]
    },
    'en': {
        'locale_code': 'eng',
        'stop_words': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'about', 'is', 'it', 'to', 'of']
    },
    'de': {
        'locale_code': 'deu',
        'stop_words': ['der', 'die', 'das', 'ein', 'eine', 'und', 'oder', 'aber', 'in', 'auf', 'zu']
    },
    'sp': {
        'locale_code': 'spa',
        'stop_words': ['el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'pero', 'en', 'a', 'de']
    },
    'pt': {
        'locale_code': 'por',
        'stop_words': ['o', 'a', 'os', 'as', 'um', 'uma', 'e', 'ou', 'mas', 'em', 'para', 'de']
    },
    'fr': {
        'locale_code': 'fra',
        'stop_words': ['le', 'la', 'les', 'un', 'une', 'et', 'ou', 'mais', 'dans', 'sur', 'à', 'pour', 'de']
    },
    'vn': {
        'locale_code': 'vie',
        'stop_words': []
    },
    'ar': {
        'locale_code': 'ara',
        'stop_words': []
    },
    'cn': {
        'locale_code': 'zho',
        'stop_words': []
    }
}

client = meilisearch.Client(MEILI_URL, MEILI_MASTER_KEY if MEILI_MASTER_KEY else None)

def setup_indexes():
    for lang, config in LANGUAGES.items():
        configure_single_index(f'site_{lang}', config['stop_words'], config.get('locale_code'))
    
    configure_single_index('site_content', [], None)

def configure_single_index(index_name, stop_words, locale_code=None):
    print(f"Настройка индекса: {index_name}...")
    index = client.index(index_name)
    
    settings = {
        'searchableAttributes': [
            'pagetitle',
            'parent_title',
            'breadcrumbs',
            'longtitle',
            'menutitle',
            'introtext',
            'description',
            'content',
            'alias'
        ],
        'localizedAttributes': [
            {'attributePatterns': ['*'], 'locales': [locale_code]}
        ] if locale_code else [],
        'filterableAttributes': [
            'id', 'published', 'deleted', 'parent', 'template', 
            'isfolder', 'searchable', 'hidemenu', 'published_year', 'page_weight'
        ],
        'sortableAttributes': [
            'publishedon', 'createdon', 'editedon', 'menuindex', 'hitcount', 'published_year', 'page_weight'
        ],
        'rankingRules': [
            'words',
            'typo',
            'proximity',
            'exactness',
            'attribute',
            'sort',
            'hitcount:desc',
            'publishedon:desc',
            'page_weight:desc'
        ],
        'stopWords': stop_words,
        'synonyms': {
            'поступление': ['прием', 'абитуриент', 'зачисление', 'поступить'],
            'прием': ['поступление', 'абитуриент', 'зачисление'],
            'абитуриент': ['поступление', 'прием', 'школьник', 'поступающий'],
            'поступить': ['поступление', 'зачисление'],
            'баллы': ['проходной', 'егэ', 'минимальный балл'],
            'проходной': ['баллы', 'егэ'],
            'егэ': ['баллы', 'проходной', 'экзамен'],
            'общежитие': ['общага', 'проживание', 'поселение', 'иногородним', 'жилье'],
            'общага': ['общежитие', 'проживание'],
            'проживание': ['общежитие', 'поселение'],
            'поселение': ['общежитие', 'проживание'],
            'стипендия': ['выплата', 'социальные выплаты'],
            'выплата': ['стипендия', 'мат. помощь'],
            'платное': ['контракт', 'коммерция', 'договор'],
            'контракт': ['платное', 'коммерция', 'договор'],
            'коммерция': ['платное', 'контракт'],
            'бюджет': ['бесплатное', 'квота'],
            'расписание': ['пары', 'график', 'звонки'],
            'пары': ['расписание', 'занятия'],
            'бакалавриат': ['бакалавр', '1 курс', 'высшее образование'],
            'магистратура': ['магистр', '2 ступень'],
            'аспирантура': ['аспирант'],
            'контакты': ['телефон', 'адрес', 'email', 'почта', 'связь'],
            'телефон': ['контакты', 'связь'],
            'о нас': ['об университете', 'информация', 'сведения', 'история'],
            'информация': ['сведения', 'о нас', 'общие сведения'],
            'общие сведения': ['информация', 'о нас'],
            'фкти': ['компьютерные технологии', 'информатика'],
            'фибс': ['информационно-измерительные', 'биотехнические'],
            'фрт': ['радиотехника', 'телекоммуникации'],
            'фэа': ['электротехника', 'автоматика'],
            'фэл': ['электроника'],
            'гф': ['гуманитарный'],
            'инпротех': ['экономика', 'менеджмент', 'инновации'],
            'вуц': ['военный учебный центр', 'военная кафедра', 'армия', 'военный центр'],
            'военная кафедра': ['вуц', 'военный учебный центр'],
            'терроризм': ['экстремизм', 'безопасность', 'игил', 'антитеррор'],
            'экстремизм': ['терроризм', 'безопасность'],
            'игил': ['терроризм', 'экстремизм'],
            'туберкулез': ['флюорография', 'справка'],
            'флюорография': ['туберкулез', 'справка', 'медосмотр'],
            'спб': ['санкт-петербург', 'петербург'],
            'санкт-петербург': ['спб', 'петербург']
        },

        'typoTolerance': {
            'enabled': True,
            'disableOnAttributes': ['alias', 'id'],
            'minWordSizeForTypos': {
                'oneTypo': 6,
                'twoTypos': 10
            }
        },
        'displayedAttributes': [
            'id', 
            'pagetitle', 
            'parent_title',
            'breadcrumbs',
            'published_year',
            'page_weight',
            'description', 
            'alias'
        ]
    }
    
    task = index.update_settings(settings)
    print(f"Обновление {index_name} запущено. Task UID: {task.task_uid}")

if __name__ == "__main__":
    setup_indexes()
