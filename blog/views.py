from django.contrib.postgres.search import TrigramSimilarity
from django.core.mail import send_mail
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.views.generic import ListView
from taggit.models import Tag

from blog.forms import CommentForm
from blog.forms import EmailPostForm
from blog.forms import SearchForm
from blog.models import Post


def post_list(request, tag_slug=None):
    objects_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        objects_list = objects_list.filter(tags__in=[tag])
    paginator = Paginator(objects_list, 4)
    page = request.GET.get('page')

    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/post/list.html', {
        'posts': posts,
        'page': page,
        'tag': tag
    })


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 4
    template_name = 'blog/post/list.html'


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published',
                             publish__year=year, publish__month=month,
                             publish__day=day)

    comments = post.comments.filter(active=True)
    new_comment = None
    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()
            comment_form = CommentForm()
    else:
        comment_form = CommentForm()

    post_tags_id = post.tags.values_list('id', flat=True)
    similar_post = Post.published.filter(tags__in=post_tags_id) \
        .exclude(id=post.id)
    similar_post = similar_post.annotate(same_tags=Count('tags')) \
        .order_by('-same_tags', '-publish')[:4]

    return render(request, 'blog/post/detail.html', {'post': post,
                                                     'comments': comments,
                                                     'new_comment':
                                                         new_comment,
                                                     'comment_form':
                                                         comment_form,
                                                     'similar_posts':
                                                         similar_post
                                                     })


def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{name} ({email}) recommends you reading' \
                      '"{post_title}"'.format(name=cd['name'],
                                              email=cd['email'],
                                              post_title=post.title)
            message = 'Read "{post_title}" at {url}\n\n {name}\'s comments: ' \
                      '{comments}'.format(post_title=post.title, url=post_url,
                                          name=cd['name'],
                                          comments=cd['comments'])
            send_mail(subject, message, 'trainingtask217@gmail.com',
                      [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {
        'post': post,
        'form': form,
        'sent': sent
    })


def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data['query']
        results = Post.objects.annotate(similarity=TrigramSimilarity(
                'title', query)) \
            .filter(similarity__gte=0.3) \
            .order_by('-similarity')
    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results
                                                     })
