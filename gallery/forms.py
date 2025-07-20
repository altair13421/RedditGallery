from django import forms
from .models import SubReddit
from .utils import get_subreddit_info

class SubRedditForm(forms.ModelForm):

    def verify_sub_reddit(self, subreddit_name):
        """Verify if the subreddit exists and is valid."""
        try:
            data = get_subreddit_info(subreddit_name, 'day', 'hot', limit=3)
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
            raise forms.ValidationError("Invalid subreddit name or subreddit does not exist.")
        if commit:
            instance.save()
            if data:
                instance.display_name = data.get('title_sub', '')
                instance.name = data.get('display_name', '')
                instance.save()
        return instance

    class Meta:
        model = SubReddit
        fields = ['sub_reddit', 'direct_url']
        widgets = {
            'sub_reddit': forms.TextInput(attrs={'class': 'form-control'}),
            'direct_url': forms.TextInput(attrs={'class': 'form-control'}),
        }

class Settings(forms.ModelForm): ...
