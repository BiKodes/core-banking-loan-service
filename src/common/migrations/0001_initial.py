from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        db_index=True,
                        help_text="Unique organization code (e.g., ORG001)",
                        max_length=50,
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Display name of the organization",
                        max_length=255,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed description of the organization",
                    ),
                ),
                (
                    "country",
                    models.CharField(
                        blank=True,
                        help_text="Country of operation",
                        max_length=100,
                    ),
                ),
                (
                    "city",
                    models.CharField(
                        blank=True,
                        help_text="City/Region of operation",
                        max_length=100,
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        help_text="Contact phone number",
                        max_length=20,
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        help_text="Contact email address",
                        max_length=254,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether the organization is active",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrganizationUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "Administrator"),
                            ("manager", "Manager"),
                            ("accountant", "Accountant"),
                            ("viewer", "Viewer"),
                            ("user", "User"),
                        ],
                        default="user",
                        help_text="Role within the organization",
                        max_length=20,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether this user is active in this organization",
                    ),
                ),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        help_text="The organization this user belongs to",
                        on_delete=models.CASCADE,
                        related_name="users",
                        to="common.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The Django user",
                        on_delete=models.CASCADE,
                        related_name="organizations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Organization User",
                "verbose_name_plural": "Organization Users",
                "ordering": ["-added_at"],
                "unique_together": {("organization", "user")},
            },
        ),
        migrations.AddIndex(
            model_name="organizationuser",
            index=models.Index(
                fields=["organization", "user"],
                name="common_orga_organiz_4418df_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="organizationuser",
            index=models.Index(
                fields=["organization", "is_active"],
                name="common_orga_organiz_bf5d4e_idx",
            ),
        ),
    ]
