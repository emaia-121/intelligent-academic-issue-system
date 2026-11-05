from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from categories.models import Category 


class Issue(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ready_for_review', 'Ready For Review'), 
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_issues'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)

    description = models.TextField()

    information_request = models.TextField(
        blank=True,
        null=True
    )

    student_information_response = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    is_complete = models.BooleanField(default=False)
    
    resolution_notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title
    
class IssueDocument(models.Model):

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE
    )

    document = models.ForeignKey(
        'documents_app.Document',
        on_delete=models.CASCADE
    )

    file = models.FileField(
        upload_to='issue_documents/'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.issue.title} - {self.document.name}"
    
class IssueActivity(models.Model):

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    action = models.CharField(
        max_length=255
    )

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issue_activities"
    )

    is_system_action = models.BooleanField(
        default=False
    )

    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        
        actor = (
            "System"
            if self.is_system_action
            else self.performed_by.username
            if self.performed_by
            else "Unknown"
        )
        return f"Issue #{self.issue.id} - {self.action} ({actor})" 

    class Meta:
        verbose_name = "Issue Activity"
        verbose_name_plural = "Issue Activities"
        ordering = ["-created_at"] 