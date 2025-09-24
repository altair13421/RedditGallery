import time
from django.conf import settings
import praw
import requests
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db import transaction
from .models import IgnoredPosts, SubReddit, Post, Gallery, Image
from django.db.utils import OperationalError
from icecream import ic

import urllib.parse

LIMIT = 1000
workers = 3
reddit_link = "https://www.reddit.com"
BASE_DIR = settings.BASE_DIR

time_frames = [
    "day",
    # "week",
    "month",
    # "year",;
    "all",
]
type_ = [
    "new",
    "hot",
    "top",
]


def reddit_client():
    return praw.Reddit(
        client_id=settings.CLIENT_ID,
        client_secret=settings.CLIENT_SECRET,
        user_agent=settings.USER_AGENT,
    )


client = reddit_client()


def get_gallery_images(post):
    media_data = list()
    post_meta: dict = {}
    if "media_metadata" in dir(post):
        post_meta = post.media_metadata
    else:
        if "crosspost_parent" in dir(post):
            post_meta = post.crosspost_parent_list[0]["media_metadata"]
    for item in list(post_meta.keys()):
        gall_data = dict()
        if "id" in list(post_meta[item].keys()):
            gall_data["img_id"] = post_meta[item]["id"]
        if "s" in list(post_meta[item].keys()):
            if "u" in list(post_meta[item]["s"].keys()):
                gall_data["image"] = post_meta[item]["s"]["u"]
            elif "mp4" in list(post_meta[item]["s"].keys()):
                gall_data["image"] = post_meta[item]["s"]["mp4"]
            elif "gif" in list(post_meta[item]["s"].keys()):
                gall_data["image"] = post_meta[item]["s"]["gif"]
        media_data.append(gall_data)
    return media_data


def get_subreddit_info(
    subreddit: str, time_frame: str, type_: str, limit: int = LIMIT
) -> list:
    try:
        sub_data = client.subreddit(f"{subreddit}")  # * minus the "r/"

        if type_ == "top":
            all_posts = sub_data.top(time_filter=time_frame, limit=limit)
        elif type_ == "hot":
            all_posts = sub_data.hot(limit=limit)
        elif type_ == "new":
            all_posts = sub_data.new(limit=limit)

        posts = list()
        posts.append(
            {
                "title_sub": sub_data.title,
                "display_name": sub_data.display_name,
            }
        )
        for post in all_posts:
            data = {
                "title": post.title,
                "content": post.selftext,
                "id": post.id,
                "score": post.score,
                # "comments": post.num_comments,
                "url": post.url,
                "perma_url": f"{reddit_link}/{post.permalink}",
            }
            try:
                if post.url.__contains__("gallery"):
                    data["media_meta"] = get_gallery_images(post)
            except Exception:
                ...
            posts.append(data)
        return posts
    except Exception:
        return None


def clean_url(url: str, file_append: str = ""):
    if url.__contains__("[/img]"):
        print_url = url.replace("[/img]", "")
    else:
        print_url = url
    # print_log(f'{print_url}', end=" || ")
    filename = None
    if url.__contains__("pictures.hentai-foundry.com"):
        pass
    elif url.__contains__("twimg"):
        pass
    elif (
        ".gifv" in url
        or ".mp4" in url
        or ".webm" in url
        or "png" in url
        or ".jpg" in url
        or "webp" in url
        or "jpeg" in url
    ):
        filename = url.split("/")[-1]
        if filename.__contains__("?"):
            filename = filename.split("?")[0]
            url = url.split("?")[0]
            if "https://preview.redd.it/" in url:
                url = url.replace("https://preview.redd.it/", "https://i.redd.it/")
        if filename.__contains__(".gifv"):
            filename = filename.replace(".gifv", ".mp4")
            url = url.replace(".gifv", ".mp4")
    elif url.__contains__("imgur.com"):
        filename = None
    if filename is not None and file_append != "":
        filename = f"{file_append}_{filename}"
    return {
        "filename": filename,
        "url": url,
        "print_url": print_url,
    }


def clean_list(download_urls: list):
    cleaned = []
    if "media_meta" in list(download_urls.keys()):
        for item in download_urls["media_meta"]:
            if "image" in list(item.keys()):
                cleaned_url = clean_url(item["image"], download_urls["id"])
                if cleaned_url["filename"] is not None:
                    cleaned.append(
                        {
                            "url": cleaned_url["url"],
                            "filename": cleaned_url["filename"],
                            "print_url": cleaned_url["print_url"],
                            "reddit_id": download_urls["id"],
                            "gallery": True,
                        }
                    )
    else:
        cleaned_url = clean_url(download_urls["url"])
        if cleaned_url["filename"] is not None:
            cleaned.append(
                {
                    "url": cleaned_url["url"],
                    "filename": cleaned_url["filename"],
                    "print_url": cleaned_url["print_url"],
                    "reddit_id": download_urls["url"],
                    "gallery": False,
                }
            )
    return cleaned


def check_if_good_image(url, retry=0):
    """
    Checks if the URL is a valid image URL.
    :param url: The URL to check.
    :return: True if the URL is a valid image, False otherwise.
    """
    try:
        headers = {
            "User-Agent": "PostmanRuntime/7.46.1",
            # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            # "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        if url.__contains__("imgur"):
            return False
        response = requests.head(url, timeout=10, headers=headers)
        # ic(response.headers)
        if response.status_code not in [200, 307]:
            ic(response.status_code, url, response.headers.get("Content-Type", ""))
            return False
        if response.status_code == 307:
            if "Location" in response.headers:
                new_url = urllib.parse.unquote(response.headers["Location"])
                if retry < 3:
                    retry += 1
                    return check_if_good_image(new_url, retry)
                return False
        content_type = response.headers.get("Content-Type", "")
        return content_type.startswith("image/")
    except requests.ConnectionError:
        return True
    except requests.Timeout as E:
        print("Request timed out", E)
        return False
    except requests.RequestException as E:
        print("Request Failed", E)
        return False


def write_posts(posts: list, sub_reddit: SubReddit):
    """
    Writes posts to the database.
    :param posts: List of posts to write.
    :param sub_reddit: SubReddit object to associate with the posts.
    """

    def create_images(post_data, post, sub_reddit):
        cleaned = clean_list(post_data)
        # ic(cleaned)
        if cleaned:
            for item in cleaned:
                if item["reddit_id"].__contains__("/"):
                    item["reddit_id"] = item["reddit_id"].split("/")[-1]
                if not check_if_good_image(item["url"]):
                    k = 0
                    while k < 3:
                        try:
                            ignored = IgnoredPosts.objects.create(
                                reddit_id=post_data["id"]
                            )
                            return
                        except OperationalError:
                            time.sleep(2)
                            k += 1
                            continue
                        except ValueError as e:
                            print(f"ValueError: {e}")
                            break
                    continue
                k = 0
                while k < 3:
                    try:
                        images = Image.objects.filter(
                            reddit_id=item["reddit_id"],
                            subreddit=sub_reddit,
                        )
                        if images.exists() and images.count() > 1:
                            images.delete()
                        image, created = Image.objects.get_or_create(
                            reddit_id=item["reddit_id"],
                            subreddit=sub_reddit,
                            link=item["url"],
                        )
                        if created:
                            image.post_ref = post
                            image.save()
                            if item["gallery"]:
                                gallery, _ = Gallery.objects.get_or_create(
                                    reddit_id=item["reddit_id"],
                                    subreddit=sub_reddit,
                                    link=post_data["url"],
                                )
                                gallery.post_ref = post
                                gallery.save()
                                image.gallery = gallery
                                image.save()
                        break
                    except OperationalError:
                        time.sleep(2)
                        k += 1
                        continue
                    except Exception as e:
                        print(f"Exception: {e}, {item['print_url']}")
                        break

    def create_posts(post_data, sub_reddit):
        """Creates or updates a post in the database."""
        if IgnoredPosts.objects.filter(reddit_id=post_data["id"]).exists():
            return
        k = 0
        while k < 3:
            try:
                # ic(post_data) if "media_meta" in post_data.keys() else None
                post, created = Post.objects.get_or_create(
                    reddit_id=post_data["id"],
                    defaults={
                        "title": post_data["title"],
                        "content": post_data["content"],
                        "link": post_data["perma_url"],
                        "score": post_data["score"],
                    },
                )
                break
            except OperationalError:
                time.sleep(2)
                k += 1
                continue
            except Exception as e:
                print(
                    f"Exception: {e}, objects {Post.objects.filter(reddit_id=post_data['id'])}"
                )
                Post.objects.filter(reddit_id=post_data["id"]).delete()
                return
        if created:
            post.subreddit = sub_reddit
            post.save()
            create_images(post_data, post, sub_reddit)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {
            executor.submit(create_posts, post_data, sub_reddit): post_data["id"]
            for post_data in posts
        }
        for future in as_completed(future_to_url):
            future.result()
    # for post in posts:
    # create_posts(post, sub_reddit)


###################### BULKING AND SOMETHING ######################


def write_posts_bulk(posts: list, sub_reddit: SubReddit):
    """
    Optimized bulk version using transaction.atomic and batch processing.
    """

    @transaction.atomic
    def process_batch(batch_posts, sub_reddit):
        """Process a batch of posts atomically"""
        if not batch_posts:
            return

        # batch_size = len(batch_posts)
        # print(f"Processing batch of {batch_size} posts...")

        # Step 1: Filter out ignored posts and existing posts
        post_ids = [post["id"] for post in batch_posts]

        # Check ignored posts
        ignored_ids = set(
            IgnoredPosts.objects.filter(reddit_id__in=post_ids).values_list(
                "reddit_id", flat=True
            )
        )

        # Check existing posts
        existing_posts = Post.objects.filter(reddit_id__in=post_ids)
        existing_post_map = {p.reddit_id: p for p in existing_posts}

        # Filter valid posts (not ignored and not existing)
        valid_posts = [
            p
            for p in batch_posts
            if p["id"] not in ignored_ids and p["id"] not in existing_post_map
        ]

        if not valid_posts:
            # print("No new posts to create in this batch")
            return

        # Step 2: Bulk create posts
        posts_to_create = []
        for post_data in valid_posts:
            posts_to_create.append(
                Post(
                    reddit_id=post_data["id"],
                    title=post_data["title"][:500],  # Limit length if needed
                    content=post_data["content"],
                    link=post_data["perma_url"],
                    score=post_data["score"],
                    subreddit=sub_reddit,
                )
            )

        # Bulk create posts
        created_posts = Post.objects.bulk_create(posts_to_create)
        created_post_map = {p.reddit_id: p for p in created_posts}
        # print(f"Created {len(created_posts)} new posts")

        # Step 3: Process images for newly created posts
        images_to_create = []
        galleries_to_create = []
        gallery_image_map = {}  # Track which images belong to which galleries

        for post_data in valid_posts:
            if post_data["id"] in created_post_map:
                post = created_post_map[post_data["id"]]
                cleaned_images = clean_list(post_data)

                if cleaned_images:
                    for item in cleaned_images:
                        # Clean reddit_id
                        reddit_id = item["reddit_id"]
                        if "/" in reddit_id:
                            reddit_id = reddit_id.split("/")[-1]

                        # Skip bad images
                        if not check_if_good_image(item["url"]):
                            # Mark post as ignored
                            IgnoredPosts.objects.get_or_create(
                                reddit_id=post_data["id"]
                            )
                            continue

                        # Create image
                        images_to_create.append(
                            Image(
                                reddit_id=reddit_id,
                                subreddit=sub_reddit,
                                link=item["url"],
                                post_ref=post,
                            )
                        )

                        # Handle galleries
                        if item.get("gallery", False):
                            galleries_to_create.append(
                                Gallery(
                                    reddit_id=reddit_id,
                                    subreddit=sub_reddit,
                                    link=post_data["url"],
                                    post_ref=post,
                                )
                            )
                            # Track that this image belongs to a gallery
                            gallery_image_map[reddit_id] = post_data["id"]

        # Step 4: Bulk create images and galleries
        if images_to_create:
            created_images = Image.objects.bulk_create(
                images_to_create, ignore_conflicts=True  # Skip duplicates
            )
            # print(f"Created {len(images_to_create)} images")

        if galleries_to_create:
            created_galleries = Gallery.objects.bulk_create(
                galleries_to_create, ignore_conflicts=True
            )
            # print(f"Created {len(galleries_to_create)} galleries")

            # Associate images with their galleries (this requires individual updates)
            gallery_map = {g.reddit_id: g for g in created_galleries}
            for image in created_images:
                if image.reddit_id in gallery_map:
                    image.gallery = gallery_map[image.reddit_id]

            # Bulk update the gallery associations
            Image.objects.bulk_update(created_images, ["gallery"])

    def safe_process_batch(batch, sub_reddit, max_retries=3):
        """Wrapper with retry logic for database locks"""
        for attempt in range(max_retries):
            try:
                process_batch(batch, sub_reddit)
                break  # Success
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"Database locked, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Failed after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                print(f"Unexpected error: {e}")
                raise

    # Step 5: Process all posts in manageable batches
    batch_size = 20  # Adjust based on your system's capacity
    total_posts = len(posts)

    # print(f"Starting bulk processing of {total_posts} posts...")

    for i in range(0, total_posts, batch_size):
        batch = posts[i : i + batch_size]
        safe_process_batch(batch, sub_reddit)

        # progress = min(i + batch_size, total_posts)
        # print(f"Progress: {progress}/{total_posts} posts processed")

    print(f"Bulk processing completed! {total_posts} posts processed.")


# Alternative: Simpler version that's easier to debug
def write_posts_simple_bulk(posts: list, sub_reddit: SubReddit):
    """
    Simpler bulk version that processes one post at a time but uses atomic transactions.
    """

    @transaction.atomic
    def process_single_post(post_data, sub_reddit):
        """Process a single post atomically"""
        # Check if post should be ignored
        if IgnoredPosts.objects.filter(reddit_id=post_data["id"]).exists():
            return False

        # Check if post already exists
        if Post.objects.filter(reddit_id=post_data["id"]).exists():
            return False

        # Create the post
        post = Post.objects.create(
            reddit_id=post_data["id"],
            title=post_data["title"],
            content=post_data["content"],
            link=post_data["perma_url"],
            score=post_data["score"],
            subreddit=sub_reddit,
        )

        # Process images
        cleaned_images = clean_list(post_data)
        if cleaned_images:
            for item in cleaned_images:
                reddit_id = item["reddit_id"]
                if "/" in reddit_id:
                    reddit_id = reddit_id.split("/")[-1]

                if not check_if_good_image(item["url"]):
                    IgnoredPosts.objects.get_or_create(reddit_id=post_data["id"])
                    continue

                # Create image
                image = Image.objects.create(
                    reddit_id=reddit_id,
                    subreddit=sub_reddit,
                    link=item["url"],
                    post_ref=post,
                )

                # Create gallery if needed
                if item.get("gallery", False):
                    gallery = Gallery.objects.create(
                        reddit_id=reddit_id,
                        subreddit=sub_reddit,
                        link=post_data["url"],
                        post_ref=post,
                    )
                    image.gallery = gallery
                    image.save()

        return True

    # Process posts with limited concurrency
    successful = 0
    for i, post_data in enumerate(posts):
        try:
            if process_single_post(post_data, sub_reddit):
                successful += 1
        except Exception as e:
            print(f"Error processing post {post_data['id']}: {e}")

        # Progress tracking
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(posts)} posts, {successful} successful")

    print(f"Completed: {successful}/{len(posts)} posts processed successfully")


######################## END BULKING #########################


def get_posts(subreddit: SubReddit):
    for time in time_frames:
        for type_of in type_:
            if type_of in ["hot", "new"]:
                if time != "day":
                    continue

            print("processed subreddit: ", subreddit.sub_reddit, time, type_of)
            posts = get_subreddit_info(subreddit.sub_reddit, time, type_of)
            try:
                subreddit.display_name = posts[0]["title_sub"]
                subreddit.name = posts[0]["display_name"]
                subreddit.save()
            except:
                pass
            if posts:
                write_posts_bulk(posts[1:], subreddit)


def sync_data_with_json(json_data):
    if isinstance(json_data, list):
        for sub in json_data:
            sub_red, created = SubReddit.objects.get_or_create(
                sub_reddit=sub,
                defaults={
                    "name": sub,
                    "direct_url": f"https://www.reddit.com/r/{sub}/",
                    "is_active": True,
                },
            )
            get_posts(sub_red)


def sync_data():
    """
    Syncs data from the Reddit API to the local database.
    This function should be called periodically to keep the database updated.
    """
    subreddits = SubReddit.objects.filter(is_active=True).order_by("-id")
    for subreddit in subreddits:
        get_posts(subreddit)


def sync_singular(sub: SubReddit):
    """
    Syncs data for a specific subreddit.
    :param sub: SubReddit object to sync.
    """
    get_posts(sub)
