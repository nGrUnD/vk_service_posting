from src.models.category import CategoryOrm
from src.repositories.base import BaseRepository
from src.schemas.category import Category


class CategoryRepository(BaseRepository):
    model = CategoryOrm
    schema = Category

    def get_categories(self, skip: int = 0, limit: int = 100):
        return self.session.query(Category).offset(skip).limit(limit).all()