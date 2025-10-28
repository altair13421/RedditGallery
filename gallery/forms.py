from django import forms
from .models import MainSettings, SubReddit, Category
from .utils import get_subreddit_info
import os


class SubRedditForm(forms.ModelForm):
    def verify_sub_reddit(self, subreddit_name):
        """Verify if the subreddit exists and is valid."""
        try:
            data = get_subreddit_info(subreddit_name, "day", "hot", limit=3)
            if data:
                data_sub = data[0]
                if len(data[1:]) > 0:
                    return True, data_sub
                else:
                    return False, None
            else:
                return False, None
        except Exception as e:
            print(f"Error verifying subreddit: {e}")
            return False

    def save(self, commit=True):
        instance = super().save(commit=False)
        # You can add any custom save logic here if needed
        subreddit_name = instance.sub_reddit.strip().lower()
        is_valid, data = self.verify_sub_reddit(subreddit_name)
        if not is_valid:
            raise forms.ValidationError(
                "Invalid subreddit name or subreddit does not exist."
            )
        if commit:
            instance.save()
            if data:
                instance.display_name = data.get("title_sub", "")
                instance.name = data.get("display_name", "")
                instance.save()
        return instance

    class Meta:
        model = SubReddit
        fields = ["sub_reddit", "direct_url"]
        widgets = {
            "sub_reddit": forms.TextInput(attrs={"class": "form-control"}),
            "direct_url": forms.TextInput(attrs={"class": "form-control"}),
        }


class SettingsForm(forms.ModelForm):
    def save(self, commit=...):
        instance: MainSettings = MainSettings.get_or_create_settings()
        instance.client_id = self.cleaned_data.get("client_id")
        instance.client_secret = self.cleaned_data.get("client_secret")
        instance.user_agent = self.cleaned_data.get("user_agent")
        instance.exluded_subreddits = self.cleaned_data.get("exluded_subreddits")
        instance.exluded_subreddits = (
            ",".join(instance.exluded_subreddits)
            if type(instance.exluded_subreddits) is list
            else instance.exluded_subreddits
        )
        instance.downloads_folder = self.cleaned_data.get("downloads_folder")
        for sub in instance.exluded_subreddits.split(","):
            sub_rd = SubReddit.objects.filter(sub_reddit=sub.strip())
            if sub_rd.exists():
                sub_rd = sub_rd.first()
                sub_rd.excluded = True
                sub_rd.save()
        SubReddit.objects.filter(excluded=True).exclude(
            sub_reddit__in=[
                sub.strip() for sub in instance.exluded_subreddits.split(",")
            ]
        ).update(excluded=False)

        if instance.downloads_folder:
            instance.downloads_folder = os.path.abspath(instance.downloads_folder)
        if commit:
            instance.save()
        return instance

    class Meta:
        model = MainSettings
        fields = (
            "client_id",
            "client_secret",
            "user_agent",
            "exluded_subreddits",
            "downloads_folder",
        )
        widgets = {
            "client_id": forms.PasswordInput(
                attrs={"class": "form-control", "help_text": "Your Reddit client ID"}
            ),
            "client_secret": forms.PasswordInput(
                attrs={
                    "class": "form-control",
                    "help_text": "Your Reddit client secret",
                }
            ),
            "user_agent": forms.TextInput(
                attrs={"class": "form-control", "help_text": "Your Reddit user agent"}
            ),
            "downloads_folder": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "help_text": "Path where downloads will be saved",
                }
            ),
            "exluded_subreddits": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Comma-separated list of subreddits to ignore, e.g., 'pics,funny,aww'",
                    "help_text": "Subreddits to ignore, minus the r/ prefix",
                }
            ),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Description"}
            ),
        }


class SubSettingsForm(forms.Form):
    folder_id = forms.IntegerField(widget=forms.HiddenInput())  # Add this field
    sub_display_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
    )

    excluded = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    # Use ModelMultipleChoiceField instead
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "form-check-input"},
        ),
        required=False,
    )

    # Add field for new category
    new_category = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Add new category"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
