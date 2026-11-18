from core.blogger_publisher import get_blogger_service, execute_with_retry

service = get_blogger_service()
blog = execute_with_retry(service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com'))
blog_id = blog['id']
print(f'Blog ID: {blog_id}')

# List all drafts and delete matching ones
page_token = None
deleted = []
while True:
    res = execute_with_retry(service.posts().list(blogId=blog_id, status=['DRAFT'], maxResults=100, pageToken=page_token, view='ADMIN'))
    for item in res.get('items', []):
        title = item.get('title', '')
        if any(kw in title for kw in ['Quito', 'Ichkeul', 'Auschwitz']):
            post_id = item['id']
            print(f'DELETING: {title} (ID: {post_id})')
            execute_with_retry(service.posts().delete(blogId=blog_id, postId=post_id))
            deleted.append(title)
    page_token = res.get('nextPageToken')
    if not page_token:
        break
print(f'Deleted {len(deleted)} drafts: {deleted}')