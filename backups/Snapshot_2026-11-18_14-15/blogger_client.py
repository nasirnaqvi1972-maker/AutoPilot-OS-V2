from core.blogger_publisher import get_blogger_service

def list_posts():
    service = get_blogger_service()
    blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
    blog_id = blog['id']

    posts = []
    tok = None
    
    print("Connecting to Blogger API...")
    while True:
        res = service.posts().list(
            blogId=blog_id, 
            status='LIVE', 
            maxResults=50, 
            pageToken=tok
        ).execute()
        
        items = res.get('items', [])
        for item in items:
            posts.append({
                'id': item['id'],
                'title': item.get('title', 'Untitled'),
                'url': item.get('url', ''),
                'content': item.get('content', '')
            })
            
        tok = res.get('nextPageToken')
        if not tok:
            break
            
    return posts