# Implementation Plan: Рефакторинг формы создания проблем

**Branch**: `11-problem-registration-refactor` | **Date**: 2026-01-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `spec.md`

## Summary

Рефакторинг формы создания проблем для упрощения UX: удаление избыточных полей (owner, sources), добавление ручного ввода тегов с автодополнением, изменение текста кнопки и перенаправления после создания.

## Technical Context

**Language/Version**: Python 3.x, Django 5.2.4  
**Primary Dependencies**: Django, Django REST Framework 3.16.0, jQuery  
**Storage**: PostgreSQL (основная), MongoDB (дополнительная), Redis (кэш)  
**Testing**: Django TestCase, pytest  
**Target Platform**: Web application (Linux server)  
**Project Type**: Web (Django MVC)  
**Performance Goals**: < 300ms для автодополнения тегов  
**Constraints**: Обратная совместимость с существующими аргументами  
**Scale/Scope**: MVP для социальной сети "Инкубатор идей"

## Constitution Check

Проект соответствует конституции:
- Используем существующие модели (Contention, Noun)
- Минимальные изменения в архитектуре
- Сохраняем обратную совместимость

## Project Structure

### Documentation (this feature)

```text
.specify/features/11-problem-registration-refactor/
├── spec.md              # Спецификация фичи (создана)
├── plan.md              # Этот файл
└── tasks.md             # Задачи (будет создан)
```

### Source Code (repository structure)

```text
web/
├── premises/
│   ├── models.py        # Contention - модель проблемы (без изменений)
│   ├── views.py         # ArgumentCreationView - рефакторинг
│   ├── forms.py         # ArgumentCreationForm → ProblemCreationForm
│   └── urls.py          # Возможно понадобится route для autocomplete
├── nouns/
│   ├── models.py        # Noun - модель тега (без изменений)
│   └── views.py         # Добавить endpoint для autocomplete тегов
├── api/
│   └── views.py         # Возможно добавить API для тегов
├── templates/
│   └── premises/
│       ├── new_contention.html  # Рефакторинг формы
│       ├── tree_view.html       # Добавить отображение тегов
│       ├── list_view.html       # Добавить отображение тегов
│       └── base_contention.html # Возможно добавить теги
├── static/
│   └── js/
│       └── lib/
│           └── main.js  # Добавить autocomplete для тегов
└── locale/              # Переводы для новых строк
```

## Implementation Phases

### Phase 1: Рефакторинг формы (Backend)

**Цель**: Изменить форму создания проблемы

**Изменения**:

1. **web/premises/forms.py** - Создать новую форму или изменить существующую:
   ```python
   class ProblemCreationForm(forms.ModelForm):
       tags_input = forms.CharField(
           required=False, 
           label=_("Теги"),
           help_text=_("Введите теги через запятую"),
           widget=forms.TextInput(attrs={
               'placeholder': 'транспорт, экология, город',
               'class': 'tags-input',
               'autocomplete': 'off'
           })
       )
       
       class Meta:
           model = Contention
           fields = ['title']  # Убираем owner, sources
           widgets = {
               'title': forms.Textarea(attrs={
                   'rows': 5,
                   'placeholder': _('Опишите проблему, которую хотите решить...'),
                   'minlength': 10,
                   'maxlength': 5000
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
           
           tags = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
           
           if len(tags) > 10:
               raise ValidationError(_('Максимум 10 тегов'))
           
           for tag in tags:
               if len(tag) < 2:
                   raise ValidationError(_('Минимальная длина тега - 2 символа'))
               if len(tag) > 30:
                   raise ValidationError(_('Максимальная длина тега - 30 символов'))
           
           return tags
   ```

2. **web/premises/views.py** - Обновить `ArgumentCreationView`:
   ```python
   class ArgumentCreationView(LoginRequiredMixin, CreateView):
       template_name = "premises/new_contention.html"
       form_class = ProblemCreationForm  # Новая форма
       
       def form_valid(self, form):
           form.instance.user = self.request.user
           form.instance.ip_address = get_ip_address(self.request)
           form.instance.language = normalize_language_code(get_language())
           form.instance.is_published = True
           response = super().form_valid(form)
           
           # Обработка тегов
           tags = form.cleaned_data.get('tags_input', [])
           for tag_text in tags:
               noun, created = Noun.objects.get_or_create(
                   text=tag_text,
                   language=form.instance.language,
                   defaults={'is_active': True}
               )
               form.instance.nouns.add(noun)
           
           form.instance.update_sibling_counts()
           form.instance.save_nouns()  # Автоматическое извлечение тегов
           form.instance.save()
           
           return redirect(form.instance.get_absolute_url())  # Redirect на просмотр, не на edit
   ```

### Phase 2: Рефакторинг формы (Frontend)

**Цель**: Обновить шаблон формы

**Изменения**:

1. **web/templates/premises/new_contention.html**:
   ```html
   {% extends 'base.html' %}
   {% load i18n %}

   {% block content %}
       <section class="container">
           <h1>{% trans "Создать проблему" %}</h1>
           <form action="{% url "new_argument" %}" method="post" class="problem-form">
               {% csrf_token %}
               
               <div class="form-group">
                   <label for="id_title">{% trans "Проблема" %}</label>
                   {{ form.title }}
                   {% if form.title.errors %}
                       <div class="error">{{ form.title.errors }}</div>
                   {% endif %}
               </div>
               
               <div class="form-group">
                   <label for="id_tags_input">{% trans "Теги" %} <span class="optional">({% trans "опционально" %})</span></label>
                   {{ form.tags_input }}
                   <div id="tags-suggestions" class="tags-suggestions"></div>
                   {% if form.tags_input.errors %}
                       <div class="error">{{ form.tags_input.errors }}</div>
                   {% endif %}
               </div>
               
               <button type="submit" class="submit btn-primary">{% trans "Найти решение" %}</button>
           </form>
       </section>
   {% endblock %}

   {% block extra-scripts %}
   <script>
   // Autocomplete для тегов
   $(function() {
       var $input = $('#id_tags_input');
       var $suggestions = $('#tags-suggestions');
       var debounceTimer;
       
       $input.on('input', function() {
           clearTimeout(debounceTimer);
           var val = $(this).val();
           var lastTag = val.split(',').pop().trim();
           
           if (lastTag.length < 2) {
               $suggestions.hide();
               return;
           }
           
           debounceTimer = setTimeout(function() {
               $.get('/nouns/autocomplete/', {q: lastTag}, function(data) {
                   if (data.length) {
                       var html = data.map(function(t) {
                           return '<div class="tag-suggestion" data-tag="' + t.text + '">' + t.text + '</div>';
                       }).join('');
                       $suggestions.html(html).show();
                   } else {
                       $suggestions.hide();
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
           $input.val(parts.join(',').replace(/^,\s*/, '') + ', ');
           $suggestions.hide();
           $input.focus();
       });
   });
   </script>
   {% endblock %}
   ```

### Phase 3: Autocomplete API

**Цель**: Создать endpoint для автодополнения тегов

**Изменения**:

1. **web/nouns/views.py** - Добавить view для autocomplete:
   ```python
   from django.http import JsonResponse
   from nouns.models import Noun
   from i18n.utils import normalize_language_code
   from django.utils.translation import get_language
   
   def tag_autocomplete(request):
       query = request.GET.get('q', '').lower().strip()
       if len(query) < 2:
           return JsonResponse([], safe=False)
       
       language = normalize_language_code(get_language())
       nouns = Noun.objects.filter(
           text__icontains=query,
           language=language,
           is_active=True
       ).values('text', 'slug')[:10]
       
       return JsonResponse(list(nouns), safe=False)
   ```

2. **web/nouns/urls.py** (создать если нет) или **web/main/urls.py** - Добавить URL:
   ```python
   path('nouns/autocomplete/', tag_autocomplete, name='tag_autocomplete'),
   ```

### Phase 4: Отображение тегов

**Цель**: Показывать теги на странице проблемы

**Изменения**:

1. **web/templates/premises/tree_view.html** - Добавить отображение тегов под заголовком:
   ```html
   <div class="tree-contention">
       <h3><span>{{ contention.formatted_title|safe }}</span></h3>
       {% if contention.nouns.exists %}
       <div class="problem-tags">
           {% for noun in contention.nouns.all %}
           <a href="{{ noun.get_absolute_url }}" class="tag-badge">#{{ noun.text }}</a>
           {% endfor %}
       </div>
       {% endif %}
   </div>
   ```

2. **web/templates/premises/list_view.html** - Аналогичные изменения

3. **web/static/css/main.css** (или соответствующий файл) - Стили для тегов:
   ```css
   .problem-tags {
       margin: 10px 0;
   }
   .tag-badge {
       display: inline-block;
       padding: 4px 12px;
       margin: 2px 4px;
       background: #e0e0e0;
       border-radius: 16px;
       color: #333;
       text-decoration: none;
       font-size: 0.9em;
   }
   .tag-badge:hover {
       background: #d0d0d0;
   }
   ```

### Phase 5: Переводы

**Цель**: Добавить переводы для новых строк

**Изменения**:

1. Обновить файлы локализации в `web/locale/`:
   - "Проблема"
   - "Теги"
   - "Найти решение"
   - "Минимальная длина текста проблемы - 10 символов"
   - "Максимальная длина текста проблемы - 5000 символов"
   - "Максимум 10 тегов"
   - и т.д.

### Phase 6: Тестирование

**Цель**: Убедиться что все работает

**Тесты**:

1. Unit тесты для формы:
   - Валидация длины текста проблемы
   - Валидация тегов
   - Нормализация тегов

2. Integration тесты:
   - Создание проблемы с тегами
   - Создание проблемы без тегов
   - Автодополнение тегов
   - Отображение тегов на странице

## Implementation Order

1. **Phase 1**: Форма (backend) - изменения в forms.py, views.py
2. **Phase 3**: API autocomplete - nouns/views.py, urls.py
3. **Phase 2**: Шаблон формы (frontend) - new_contention.html
4. **Phase 4**: Отображение тегов - tree_view.html, list_view.html, CSS
5. **Phase 5**: Переводы - locale files
6. **Phase 6**: Тесты

## Risks & Mitigations

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Существующие аргументы могут сломаться | Низкая | Не удаляем поля из модели, только из формы |
| Autocomplete может быть медленным | Низкая | Индекс на text поле, кэширование |
| Дублирующиеся теги | Средняя | Нормализация lowercase + unique constraint |

## Estimation

| Фаза | Время |
|------|-------|
| Phase 1: Backend форма | 2-3 часа |
| Phase 2: Frontend шаблон | 2-3 часа |
| Phase 3: Autocomplete API | 1-2 часа |
| Phase 4: Отображение тегов | 1-2 часа |
| Phase 5: Переводы | 1 час |
| Phase 6: Тестирование | 2-3 часа |
| **ИТОГО** | **9-14 часов** |
