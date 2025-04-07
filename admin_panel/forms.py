from django import forms
from .models import Channel, Category, Message, TelegramSession
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ['name', 'url', 'description', 'category', 'is_active', 'session']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'name': 'Channel name',
            'url': 'Channel link',
            'description': 'Description',
            'category': 'Category',
            'is_active': 'Status',
            'session': 'Telegram Session',
        }
        help_texts = {
            'is_active': 'Check if the channel should be active',
            'session': 'Select the Telegram session for this channel',
        }
        error_messages = {
            'name': {
                'required': "This field is required.",
                'max_length': 'Channel name is too long.'
            },
            'url': {
                'required': "This field is required.",
                'invalid': 'Enter a valid URL.'
            },
            'category': {
                'required': "This field is required.",
            },
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'session']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'session': forms.Select(attrs={'class': 'form-control'})
        }
        labels = {
            'name': 'Category name',
            'description': 'Description',
            'session': 'Telegram Session',
        }
        help_texts = {
            'name': 'Enter the category name',
            'session': 'Select the Telegram session for this category',
        }
        error_messages = {
            'name': {
                'required': "This field is required.",
                'max_length': 'Category name is too long.'
            },
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'channel', 'has_image', 'has_video', 'has_audio', 'has_document']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'channel': forms.Select(attrs={'class': 'form-control'}),
            'has_image': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_video': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_audio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_document': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'text': 'Message text',
            'channel': 'Channel',
            'has_image': 'Has Image',
            'has_video': 'Has Video',
            'has_audio': 'Has Audio',
            'has_document': 'Has Document',
        }
        help_texts = {
            'text': 'Enter the message text',
            'channel': 'Select the channel',
        }   
        error_messages = {
            'text': {
                'required': "This field is required.",
            },
            'channel': {
                'required': "This field is required.",
            },
        }

class UserRegistrationForm(UserCreationForm):
    """Form for registration of new users"""
    email = forms.EmailField(
        required=True,
        help_text='Enter a valid email address'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        """Check for uniqueness of email"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('User with this email already exists')
        return email
        
    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        
        # Hints for fields
        self.fields['username'].help_text = 'Required field. No more than 150 characters. Only letters, numbers and @/./+/-/_.'
        self.fields['password1'].help_text = ('Password must be at least 8 characters long and contain letters and numbers. ' 
                                            'Should not be similar to your login.')
        self.fields['password2'].help_text = 'Enter the same password for verification.'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

