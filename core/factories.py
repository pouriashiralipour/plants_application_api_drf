"""
User factory for generating test users.

This module uses `factory_boy` to provide a `UserFactory` class that simplifies
the creation of `User` objects in tests. It ensures that users are generated
with realistic fake data (e.g., names) and securely hashed passwords.

Features:
    - Integrates with Django ORM via `DjangoModelFactory`.
    - Uses `faker` to generate realistic first and last names.
    - Automatically handles password hashing (so `user.check_password()` works).
    - Allows specifying a custom password during user creation.
    - Provides a default password (`"defaultpassword"`) when none is given.

Example:
    >>> user = UserFactory()
    >>> user.check_password("defaultpassword")
    True

    >>> user = UserFactory(password="mypassword123")
    >>> user.check_password("mypassword123")
    True
"""

import factory
from django.contrib.auth import get_user_model

# Get the currently active user model (supports custom user models)
User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating User instances for testing.

    This factory creates instances of the `User` model with
    fake but realistic data, ensuring that required fields
    like `first_name`, `last_name`, and `password` are set properly.

    Meta:
        model (User): The custom or default Django user model.
        skip_postgeneration_save (bool): Prevents double-saving the object
            when post-generation hooks (like password setting) modify it.
    """

    class Meta:
        model = User
        skip_postgeneration_save = True

    # Faker fields for generating realistic first/last names
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """
        Post-generation hook to handle password setting.

        Args:
            create (bool): Whether the instance has been saved to the database.
                - True if the instance was created and saved.
                - False if only built (not saved).
            extracted (str, optional): A user-provided password.
                - If provided, this value will be hashed and stored.
                - If not provided, a default password (`"defaultpassword"`) is used.
            **kwargs: Additional keyword arguments (not used here).

        Behavior:
            - If `create` is False (build only, no save), do nothing.
            - If a password is provided (`extracted`), hash and save it.
            - If no password is provided, set a default password and save.

        Example:
            >>> user = UserFactory(password="mypassword123")
            >>> user.check_password("mypassword123")
            True
        """

        if not create:
            # If the object isn't saved to DB yet, don't try setting a password
            return

        if extracted:
            # If caller passed a password, use it
            self.set_password(extracted)

        else:
            # Otherwise, use a default password
            self.set_password("defaultpassword")

        # Save after setting password, since hashing modifies the instance
        self.save()
