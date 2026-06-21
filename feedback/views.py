from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Suggestion, Bug
from .forms import SuggestionForm, BugForm

@login_required
def add_suggestion(request):
    if request.method == 'POST':
        form = SuggestionForm(request.POST)
        if form.is_valid():
            suggestion = form.save(commit=False)
            suggestion.user = request.user
            suggestion.save()
            messages.success(request, "Предложение отправлено! Спасибо за ваш вклад.")
            return redirect('feedback:my_suggestions')
    else:
        form = SuggestionForm()
    return render(request, 'feedback/add_suggestion.html', {'form': form})

@login_required
def add_bug(request):
    if request.method == 'POST':
        form = BugForm(request.POST)
        if form.is_valid():
            bug = form.save(commit=False)
            bug.user = request.user
            bug.save()
            messages.success(request, "Баг отправлен! Разработчики будут уведомлены.")
            return redirect('feedback:my_bugs')
    else:
        form = BugForm()
    return render(request, 'feedback/add_bug.html', {'form': form})

@login_required
def my_suggestions(request):
    suggestions = Suggestion.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'feedback/my_suggestions.html', {'suggestions': suggestions})

@login_required
def my_bugs(request):
    bugs = Bug.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'feedback/my_bugs.html', {'bugs': bugs})

@login_required
def all_suggestions(request):
    if not request.user.is_superuser:
        messages.error(request, "Доступ только для суперадминистратора.")
        return redirect('core:home')
    suggestions = Suggestion.objects.all().order_by('-created_at')
    return render(request, 'feedback/all_suggestions.html', {'suggestions': suggestions})

@login_required
def all_bugs(request):
    if not request.user.is_superuser:
        messages.error(request, "Доступ только для суперадминистратора.")
        return redirect('core:home')
    bugs = Bug.objects.all().order_by('-created_at')
    return render(request, 'feedback/all_bugs.html', {'bugs': bugs})

@login_required
def change_suggestion_status(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Недостаточно прав.")
        return redirect('core:home')
    suggestion = get_object_or_404(Suggestion, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Suggestion.STATUS_CHOICES):
            suggestion.status = new_status
            suggestion.save()
            messages.success(request, f"Статус предложения «{suggestion.title}» изменён на {suggestion.get_status_display()}.")
        return redirect('feedback:all_suggestions')
    return render(request, 'feedback/change_status.html', {
        'item': suggestion,
        'status_choices': Suggestion.STATUS_CHOICES,
        'type': 'suggestion'
    })

@login_required
def change_bug_status(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Недостаточно прав.")
        return redirect('core:home')
    bug = get_object_or_404(Bug, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Bug.STATUS_CHOICES):
            bug.status = new_status
            bug.save()
            messages.success(request, f"Статус бага «{bug.title}» изменён на {bug.get_status_display()}.")
        return redirect('feedback:all_bugs')
    return render(request, 'feedback/change_status.html', {
        'item': bug,
        'status_choices': Bug.STATUS_CHOICES,
        'type': 'bug'
    })

# Детальный просмотр предложения
@login_required
def suggestion_detail(request, pk):
    suggestion = get_object_or_404(Suggestion, pk=pk)
    if not (request.user.is_superuser or suggestion.user == request.user):
        messages.error(request, "У вас нет прав для просмотра этого предложения.")
        return redirect('feedback:my_suggestions')
    return render(request, 'feedback/suggestion_detail.html', {'item': suggestion})

# Детальный просмотр бага
@login_required
def bug_detail(request, pk):
    bug = get_object_or_404(Bug, pk=pk)
    if not (request.user.is_superuser or bug.user == request.user):
        messages.error(request, "У вас нет прав для просмотра этого бага.")
        return redirect('feedback:my_bugs')
    return render(request, 'feedback/bug_detail.html', {'item': bug})