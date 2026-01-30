# Tasks: Рефакторинг формы создания проблем

**Input**: Design documents from `.specify/features/11-problem-registration-refactor/`
**Prerequisites**: plan.md (required), spec.md (required)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

```text
web/
├── premises/
│   ├── forms.py        # Формы
│   └── views.py        # Views
├── nouns/
│   ├── views.py        # Autocomplete endpoint
│   └── urls.py         # URL routing
├── templates/premises/ # Шаблоны
└── static/            # CSS, JS
```

---

## Phase 1: Foundational (Backend)

**Purpose**: Основная логика формы и обработка тегов

### T001 [US1,US3] Создать новую форму ProblemCreationForm

**Файл**: `web/premises/forms.py`

**Изменения**:
```python
# Добавить после строки 6 (импорты)
from django.utils.translation import gettext_lazy as _

# Добавить после класса ArgumentCreationForm (после строки 12)
class ProblemCreationForm(forms.ModelForm):
    """Упрощенная форма для создания проблем с поддержкой тегов."""
    
    tags_input = forms.CharField(
        required=False,
        label=_("Теги"),
        help_text=_("Введите теги через запятую (максимум 10)"),
        widget=forms.TextInput(attrs={
            'placeholder': 'транспорт, экология, город',
            'class': 'tags-input',
            'autocomplete': 'off',
            'id': 'id_tags_input'
        })
    )
    
    class Meta:
        model = Contention
        fields = ['title']
        widgets = {
            'title': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': _('Опишите проблему, которую хотите решить...'),
                'class': 'problem-textarea',
                'minlength': '10',
                'maxlength': '5000'
            })
        }
        labels = {
            'title': _('Проблема')
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '')
        if len(title) < 10:
            raise ValidationError(_('Минимальная длина текста проблемы - 10 символов'))
        if len(title) > 5000:
            raise ValidationError(_('Максимальная длина текста проблемы - 5000 символов'))
        return title
    
    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if not tags_input:
            return []
        
        # Разделяем по запятой, нормализуем
        tags = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
        
        # Удаляем дубликаты, сохраняя порядок
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        tags = unique_tags
        
        if len(tags) > 10:
            raise ValidationError(_('Максимум 10 тегов'))
        
        for tag in tags:
            if len(tag) < 2:
                raise ValidationError(_('Минимальная длина тега - 2 символа'))
            if len(tag) > 30:
                raise ValidationError(_('Максимальная длина тега - 30 символов'))
        
        return tags
```

**Acceptance Criteria**:
- [ ] Форма содержит только поля `title` и `tags_input`
- [ ] Валидация длины текста проблемы (10-5000)
- [ ] Валидация тегов (2-30 символов, максимум 10)
- [ ] Теги нормализуются в lowercase
- [ ] Дубликаты тегов удаляются

---

### T002 [US1,US2] Обновить ArgumentCreationView для работы с тегами

**Файл**: `web/premises/views.py`

**Изменения**:

1. Добавить импорт (после строки 22):
```python
from premises.forms import (ArgumentCreationForm, PremiseCreationForm,
                            PremiseEditForm, ReportForm, ProblemCreationForm)
```

2. Изменить класс `ArgumentCreationView` (строки 579-605):
```python
class ArgumentCreationView(LoginRequiredMixin, CreateView):
    template_name = "premises/new_contention.html"
    form_class = ProblemCreationForm  # Заменить ArgumentCreationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Создать проблему")
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.ip_address = get_ip_address(self.request)
        form.instance.language = normalize_language_code(get_language())
        form.instance.is_published = True
        response = super().form_valid(form)
        
        # Обработка ручных тегов
        tags = form.cleaned_data.get('tags_input', [])
        if tags:
            from nouns.models import Noun
            for tag_text in tags:
                noun, created = Noun.objects.get_or_create(
                    text=tag_text,
                    language=form.instance.language,
                    defaults={'is_active': True}
                )
                form.instance.nouns.add(noun)
        
        form.instance.update_sibling_counts()
        form.instance.save_nouns()  # Автоматическое извлечение тегов из текста
        form.instance.save()
        
        # Redirect на страницу просмотра проблемы (не на edit)
        return redirect(form.instance.get_absolute_url())
```

**Acceptance Criteria**:
- [ ] Используется новая форма ProblemCreationForm
- [ ] Теги сохраняются в БД при создании проблемы
- [ ] После создания пользователь перенаправляется на страницу просмотра
- [ ] Автоматическое извлечение тегов из текста сохраняется (save_nouns)

---

### T003 [US1] Добавить endpoint для автодополнения тегов

**Файл**: `web/nouns/views.py` (создать или дополнить)

**Изменения**:

Проверить существует ли файл, если нет - создать:
```python
from django.http import JsonResponse
from django.utils.translation import get_language
from i18n.utils import normalize_language_code
from nouns.models import Noun


def tag_autocomplete(request):
    """
    AJAX endpoint для автодополнения тегов.
    GET /nouns/autocomplete/?q=<query>
    """
    query = request.GET.get('q', '').lower().strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    language = normalize_language_code(get_language())
    
    nouns = Noun.objects.filter(
        text__icontains=query,
        language=language,
        is_active=True
    ).values('text', 'slug').order_by('text')[:10]
    
    return JsonResponse(list(nouns), safe=False)
```

**Acceptance Criteria**:
- [ ] Endpoint возвращает JSON список тегов
- [ ] Фильтрация по языку пользователя
- [ ] Минимум 2 символа для поиска
- [ ] Максимум 10 результатов

---

### T004 [US1] Добавить URL для автодополнения тегов

**Файл**: `web/main/urls.py` (или создать `web/nouns/urls.py`)

**Изменения**:

Добавить в urlpatterns:
```python
from nouns.views import tag_autocomplete

# Добавить в urlpatterns
path('nouns/autocomplete/', tag_autocomplete, name='tag_autocomplete'),
```

**Acceptance Criteria**:
- [ ] URL доступен по адресу /nouns/autocomplete/
- [ ] Возвращает JSON при GET запросе

---

## Phase 2: Frontend (Templates & JS)

**Purpose**: Обновление UI формы и добавление интерактивности

### T005 [US1,US3] Обновить шаблон формы создания проблемы

**Файл**: `web/templates/premises/new_contention.html`

**Полное содержимое**:
```html
{% extends 'base.html' %}
{% load i18n %}

{% block content %}
    <section class="container problem-creation">
        <h1>{% trans "Создать проблему" %}</h1>
        <form action="{% url "new_argument" %}" method="post" class="problem-form">
            {% csrf_token %}
            
            <div class="form-group">
                <label for="id_title">{{ form.title.label }}</label>
                {{ form.title }}
                {% if form.title.help_text %}
                    <small class="help-text">{{ form.title.help_text }}</small>
                {% endif %}
                {% if form.title.errors %}
                    <div class="error-message">{{ form.title.errors }}</div>
                {% endif %}
            </div>
            
            <div class="form-group">
                <label for="id_tags_input">
                    {{ form.tags_input.label }}
                    <span class="optional">({% trans "опционально" %})</span>
                </label>
                {{ form.tags_input }}
                <div id="tags-suggestions" class="tags-suggestions"></div>
                {% if form.tags_input.help_text %}
                    <small class="help-text">{{ form.tags_input.help_text }}</small>
                {% endif %}
                {% if form.tags_input.errors %}
                    <div class="error-message">{{ form.tags_input.errors }}</div>
                {% endif %}
            </div>
            
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">{% trans "Найти решение" %}</button>
            </div>
        </form>
    </section>
{% endblock %}

{% block extra-scripts %}
<script>
$(function() {
    var $input = $('#id_tags_input');
    var $suggestions = $('#tags-suggestions');
    var debounceTimer;
    
    function getLastTag(value) {
        var parts = value.split(',');
        return parts[parts.length - 1].trim();
    }
    
    $input.on('input', function() {
        clearTimeout(debounceTimer);
        var val = $(this).val();
        var lastTag = getLastTag(val);
        
        if (lastTag.length < 2) {
            $suggestions.hide().empty();
            return;
        }
        
        debounceTimer = setTimeout(function() {
            $.ajax({
                url: '{% url "tag_autocomplete" %}',
                data: {q: lastTag},
                success: function(data) {
                    if (data && data.length) {
                        var html = data.map(function(t) {
                            return '<div class="tag-suggestion" data-tag="' + t.text + '">' + 
                                   '<span class="tag-text">#' + t.text + '</span></div>';
                        }).join('');
                        $suggestions.html(html).show();
                    } else {
                        $suggestions.hide().empty();
                    }
                },
                error: function() {
                    $suggestions.hide().empty();
                }
            });
        }, 200);
    });
    
    $suggestions.on('click', '.tag-suggestion', function() {
        var tag = $(this).data('tag');
        var val = $input.val();
        var parts = val.split(',');
        parts.pop();
        parts.push(' ' + tag);
        var newVal = parts.join(',').replace(/^,\s*/, '');
        $input.val(newVal + ', ');
        $suggestions.hide().empty();
        $input.focus();
    });
    
    // Скрыть suggestions при клике вне
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.form-group').length) {
            $suggestions.hide();
        }
    });
    
    // Скрыть suggestions при нажатии Escape
    $input.on('keydown', function(e) {
        if (e.key === 'Escape') {
            $suggestions.hide();
        }
    });
});
</script>
{% endblock %}
```

**Acceptance Criteria**:
- [ ] Форма содержит только 2 поля (проблема, теги)
- [ ] Кнопка называется "Найти решение"
- [ ] Автодополнение работает при вводе тегов
- [ ] Клик по предложению добавляет тег

---

### T006 [US4] Добавить отображение тегов на странице проблемы (tree_view)

**Файл**: `web/templates/premises/tree_view.html`

**Изменения**: После строки 19 (после `<h3>...</h3>`):
```html
<div class="tree-contention">
    <h3><span>{{ contention.formatted_title|safe }}</span></h3>
    {% if contention.nouns.exists %}
    <div class="problem-tags">
        {% for noun in contention.nouns.all %}
        <a href="{{ noun.get_absolute_url }}" class="tag-badge" title="{% trans 'Все проблемы с тегом' %} {{ noun.text }}">#{{ noun.text }}</a>
        {% endfor %}
    </div>
    {% endif %}
</div>
```

**Acceptance Criteria**:
- [ ] Теги отображаются под заголовком проблемы
- [ ] Теги кликабельны и ведут на страницу тега
- [ ] Теги отображаются в формате "#тег"

---

### T007 [P] [US4] Добавить отображение тегов на странице проблемы (list_view)

**Файл**: `web/templates/premises/list_view.html`

**Изменения**: Аналогичные T006 - добавить блок тегов под заголовком

**Acceptance Criteria**:
- [ ] Теги отображаются в list view

---

### T008 [P] Добавить CSS стили для формы и тегов

**Файл**: `web/static/css/main.css` (или соответствующий)

**Изменения**: Добавить в конец файла:
```css
/* Problem creation form */
.problem-creation {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

.problem-form .form-group {
    margin-bottom: 20px;
}

.problem-form label {
    display: block;
    margin-bottom: 5px;
    font-weight: 600;
}

.problem-form .optional {
    font-weight: normal;
    color: #666;
    font-size: 0.9em;
}

.problem-form textarea,
.problem-form input[type="text"] {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
}

.problem-form textarea {
    min-height: 150px;
    resize: vertical;
}

.problem-form .help-text {
    display: block;
    margin-top: 5px;
    color: #666;
    font-size: 0.9em;
}

.problem-form .error-message {
    color: #d32f2f;
    margin-top: 5px;
    font-size: 0.9em;
}

.problem-form .btn-primary {
    background: #1976d2;
    color: white;
    border: none;
    padding: 12px 24px;
    font-size: 16px;
    border-radius: 4px;
    cursor: pointer;
}

.problem-form .btn-primary:hover {
    background: #1565c0;
}

/* Tags autocomplete */
.tags-suggestions {
    position: absolute;
    background: white;
    border: 1px solid #ddd;
    border-top: none;
    border-radius: 0 0 4px 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 1000;
    display: none;
}

.tag-suggestion {
    padding: 10px 12px;
    cursor: pointer;
}

.tag-suggestion:hover {
    background: #f5f5f5;
}

.tag-text {
    color: #1976d2;
}

/* Problem tags display */
.problem-tags {
    margin: 10px 0 15px;
}

.tag-badge {
    display: inline-block;
    padding: 4px 12px;
    margin: 2px 4px 2px 0;
    background: #e3f2fd;
    border-radius: 16px;
    color: #1976d2;
    text-decoration: none;
    font-size: 0.9em;
    transition: background 0.2s;
}

.tag-badge:hover {
    background: #bbdefb;
    text-decoration: none;
}
```

**Acceptance Criteria**:
- [ ] Форма имеет современный вид
- [ ] Автодополнение выглядит как выпадающий список
- [ ] Теги стилизованы как badges

---

## Phase 3: Локализация

### T009 [P] Добавить переводы

**Файлы**: `web/locale/*/LC_MESSAGES/django.po`

**Новые строки для перевода**:
- "Создать проблему"
- "Проблема"
- "Теги"
- "опционально"
- "Найти решение"
- "Минимальная длина текста проблемы - 10 символов"
- "Максимальная длина текста проблемы - 5000 символов"
- "Максимум 10 тегов"
- "Минимальная длина тега - 2 символа"
- "Максимальная длина тега - 30 символов"
- "Введите теги через запятую (максимум 10)"
- "Опишите проблему, которую хотите решить..."
- "Все проблемы с тегом"

**Команда для генерации**:
```bash
cd web && python manage.py makemessages -l ru -l en -l tr
```

**Acceptance Criteria**:
- [ ] Все новые строки добавлены в .po файлы
- [ ] Переводы скомпилированы

---

## Phase 4: Тестирование (Optional)

### T010 [P] Unit тесты для формы

**Файл**: `web/premises/tests/test_forms.py` (создать)

```python
from django.test import TestCase
from premises.forms import ProblemCreationForm

class ProblemCreationFormTest(TestCase):
    def test_valid_form(self):
        form = ProblemCreationForm(data={
            'title': 'Это тестовая проблема для проверки формы',
            'tags_input': 'тег1, тег2, тег3'
        })
        self.assertTrue(form.is_valid())
    
    def test_title_too_short(self):
        form = ProblemCreationForm(data={
            'title': 'Короткий',
            'tags_input': ''
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
    def test_too_many_tags(self):
        tags = ', '.join([f'тег{i}' for i in range(15)])
        form = ProblemCreationForm(data={
            'title': 'Это тестовая проблема для проверки формы',
            'tags_input': tags
        })
        self.assertFalse(form.is_valid())
        self.assertIn('tags_input', form.errors)
    
    def test_tags_normalized(self):
        form = ProblemCreationForm(data={
            'title': 'Это тестовая проблема для проверки формы',
            'tags_input': '  Тег1  , ТЕГ2 , тег1  '
        })
        self.assertTrue(form.is_valid())
        tags = form.cleaned_data['tags_input']
        self.assertEqual(tags, ['тег1', 'тег2'])  # lowercase, дубликаты удалены
```

**Acceptance Criteria**:
- [ ] Тесты проходят
- [ ] Покрыты основные сценарии

---

### T011 [P] Integration тест для создания проблемы

**Файл**: `web/premises/tests/test_views.py` (дополнить)

```python
from django.test import TestCase, Client
from django.urls import reverse
from profiles.models import Profile

class ProblemCreationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Profile.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_problem_with_tags(self):
        response = self.client.post(reverse('new_argument'), {
            'title': 'Как уменьшить загрязнение воздуха в городе?',
            'tags_input': 'экология, город, воздух'
        })
        # Проверяем редирект на страницу проблемы
        self.assertEqual(response.status_code, 302)
        
        # Проверяем что проблема создана с тегами
        from premises.models import Contention
        problem = Contention.objects.get(title='Как уменьшить загрязнение воздуха в городе?')
        self.assertEqual(problem.nouns.count(), 3)
```

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Phase 1: Foundational (Backend)** - нет зависимостей
   - T001 (форма) → T002 (view) - последовательно
   - T003, T004 (autocomplete) - можно параллельно с T001, T002

2. **Phase 2: Frontend** - зависит от Phase 1
   - T005 (шаблон) - зависит от T001, T002, T003, T004
   - T006, T007 (отображение тегов) - можно параллельно
   - T008 (CSS) - можно параллельно

3. **Phase 3: Локализация** - зависит от Phase 1
   - T009 - после T001, T002, T005

4. **Phase 4: Тестирование** - зависит от Phase 1, 2
   - T010, T011 - параллельно, после T001-T005

### Recommended Order

```
T001 → T002 → T003 → T004 → T005 → T006, T007, T008 (parallel) → T009 → T010, T011 (parallel)
```

### Parallel Opportunities

```bash
# После T004:
Task T006: "Отображение тегов в tree_view"
Task T007: "Отображение тегов в list_view"
Task T008: "CSS стили"

# После T005:
Task T010: "Unit тесты"
Task T011: "Integration тесты"
```

---

## Checklist

### User Story 1 - Создание проблемы с тегами (P1)
- [ ] T001 - Форма с валидацией
- [ ] T002 - View с обработкой тегов
- [ ] T003 - Autocomplete endpoint
- [ ] T004 - URL routing
- [ ] T005 - Шаблон с JS

### User Story 2 - Создание проблемы без тегов (P2)
- [ ] T002 - View (теги опциональны)

### User Story 3 - Упрощенная форма (P1)
- [ ] T001 - Только 2 поля
- [ ] T005 - Кнопка "Найти решение"
- [ ] T008 - CSS стили

### User Story 4 - Фильтрация по тегам (P3)
- [ ] T006 - Теги в tree_view
- [ ] T007 - Теги в list_view
- [ ] (Страница /nouns/<slug>/ уже существует)

---

## Notes

- Все файлы в директории `web/`
- Не удаляем поля из модели Contention (обратная совместимость)
- Сохраняем существующую форму ArgumentCreationForm (для возможного rollback)
- jQuery уже есть в проекте
