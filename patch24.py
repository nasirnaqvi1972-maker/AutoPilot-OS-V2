p='safe_batch.py'
s=open(p,encoding='utf-8').read()
old='''    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=[]
    )'''
new='''    # Check for existing draft with same title
    existing_id = None
    try:
        service = None
        from core.blogger_publisher import get_blogger_service
        service = get_blogger_service()
        blog = service.blogs().getByUrl(url='https://dustanddynasty.blogspot.com').execute()
        blog_id = blog['id']
        drafts = service.posts().list(blogId=blog_id, status='DRAFT', maxResults=100).execute().get('items', [])
        for d in drafts:
            if d.get('title','').strip().lower() == title.strip().lower():
                existing_id = d['id']
                break
    except Exception as e:
        print(f"  [draft check] failed: {e}")
    if existing_id:
        print(f"  [Engine] UPDATED existing draft (ID: {existing_id}) in place. No duplicates created.")
    else:
        print("  [Engine] CREATED new draft.")

    post_id = publish_post(
        html_path=curated_html_path,
        img_folder=img_folder,
        title=title,
        labels=[],
        post_id=existing_id
    )'''
assert old in s
s=s.replace(old,new)
open(p,'w',encoding='utf-8').write(s)
print('done')
