import os
from django.conf import settings
import praw
import requests
import json
from bs4 import BeautifulSoup as bs
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import IgnoredPosts, SubReddit, Post, Gallery, Image, Deleted

limit = 1000
workers = 10
reddit_link = "https://www.reddit.com"
BASE_DIR = settings.BASE_DIR
# check if download directory exists, if not create it

time_frames = [
    "day",
    # "week",
    "month",
    # "year",
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


def get_subreddit_info(subreddit: str, time_frame: str, type_: str) -> list:
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
            except Exception as E:
                ...
            posts.append(data)
        return posts
    except Exception as E:
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
    elif url.__contains__(".png"):
        filename = url.split("/")[-1]
    elif url.__contains__(".jpg"):
        filename = url.split("/")[-1]
    elif url.__contains__(".jpeg"):
        filename = url.split("/")[-1]
    elif url.__contains__(".webp"):
        filename = url.split("/")[-1]
    elif url.__contains__(".mp4"):
        filename = url.split("/")[-1]
    elif url.__contains__(".gif"):
        if url.__contains__(".gifv"):
            url = url.replace(".gifv", ".mp4")
            filename = url.split("/")[-1]
        else:
            filename = url.split("/")[-1]
    elif url.__contains__(".webm"):
        filename = url.split("/")[-1]
    elif url.__contains__(".mkv"):
        filename = url.split("/")[-1]
    elif url.__contains__("https://imgur.com/"):
        if url.__contains__("/a/"):
            try:
                link_response = requests.get(url, timeout=10)
                if link_response.status_code == 200:
                    parser = bs(link_response.text, "html.parser")
                    try:
                        url = parser.find(
                            "meta", {"property": "og:video:secure_url"}
                        ).attrs["content"]
                    except:
                        url = parser.find("meta", {"property": "og:image"}).attrs[
                            "content"
                        ]
                    filename = f"{url.split('/')[-1]}"
                else:
                    # print_error(
                    #     f"Link Status: {link_response.status_code} || Response: {link_response} || {print_url}"
                    # )
                    ...
            except:
                pass
        else:
            url = url.replace("https://imgur.com/", "https://i.imgur.com/")
            url = url + ".png"
            filename = f"{url.split('/')[-1]}"
    if filename is not None and filename.__contains__("?"):
        filename = filename.split("?")[0]
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


def check_if_good_image(url):
    """
    Checks if the URL is a valid image URL.
    :param url: The URL to check.
    :return: True if the URL is a valid image, False otherwise.
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        return content_type.startswith("image/")
    except requests.Timeout:
        return False
    except requests.RequestException:
        return False


def write_posts(posts: list, sub_reddit: SubReddit):
    """
    Writes posts to the database.
    :param posts: List of posts to write.
    :param sub_reddit: SubReddit object to associate with the posts.
    """

    def create_posts(post_data, sub_reddit):
        """Creates or updates a post in the database."""
        if IgnoredPosts.objects.filter(reddit_id=post_data["id"]).exists():
            return
        post, created = Post.objects.get_or_create(
            reddit_id=post_data["id"],
            defaults={
                "title": post_data["title"],
                "content": post_data["content"],
                "link": post_data["perma_url"],
                "score": post_data["score"],
            },
        )
        if created:
            post.subreddit = sub_reddit
            post.save()
            cleaned = clean_list(post_data)
            if cleaned:
                for item in cleaned:
                    if item["reddit_id"].__contains__("/"):
                        item["reddit_id"] = item["reddit_id"].split("/")[-1]
                    if not check_if_good_image(item["url"]):
                        ignored= IgnoredPosts.objects.create(
                            reddit_id=post.reddit_id
                        )
                        continue
                    image, created = Image.objects.get_or_create(
                        reddit_id=item["reddit_id"],
                        defaults={
                            "link": item["url"],
                            "subreddit": sub_reddit,
                        },
                    )
                    if created:
                        image.post_ref = post
                        image.save()
                        if item["gallery"]:
                            gallery, _ = Gallery.objects.get_or_create(
                                reddit_id=item["reddit_id"],
                                defaults={
                                    "link": item["url"],
                                    "subreddit": sub_reddit,
                                },
                            )
                            gallery.post_ref = post
                            gallery.save()
                            image.gallery = gallery
                            image.save()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {
            executor.submit(create_posts, post_data, sub_reddit): post_data["id"]
            for post_data in posts
        }
        for future in as_completed(future_to_url):
            future.result()


def get_posts(subreddit: SubReddit):
    for time in time_frames:
        for type_of in type_:
            if type_of in ["hot", "new"]:
                if time != "day":
                    continue

            print("processed subreddit: ", subreddit.sub_reddit, time, type_of)
            posts = get_subreddit_info(subreddit.sub_reddit, time, type_of)
            subreddit.name = posts[0]["title_sub"]
            subreddit.display_name = posts[0]["display_name"]
            subreddit.save()
            if posts:
                write_posts(posts[1:], subreddit)


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
    subreddits = SubReddit.objects.filter(is_active=True)
    for subreddit in subreddits:
        get_posts(subreddit)
