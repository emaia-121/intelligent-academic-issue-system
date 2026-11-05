from django.db import models
from departments.models import Department
from documents_app.models import Document 

class Category(models.Model):
    name = models.CharField(max_length=120)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)

    documents = models.ManyToManyField(Document, blank=True)

    def __str__(self):
        return self.name
    
    def required_documents(self):
        return self.documents.all()

    class Meta:
        ordering = ["name"]

        verbose_name = "Category"
        verbose_name_plural = "Categories" 
# Create your models here.