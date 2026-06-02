import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "campus-gallery-dev-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'campus_gallery.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    LANGUAGES = ["zh", "en"]
    DEFAULT_LANGUAGE = "zh"

    CATEGORIES = [
        ("hardware_robot", {"zh": "智能硬件与机器人", "en": "Smart Hardware & Robotics"}),
        ("software_ai", {"zh": "软件开发与人工智能", "en": "Software Development & AI"}),
        ("life_science", {"zh": "生命科学与环境", "en": "Life Science & Environment"}),
        ("social_design", {"zh": "社会科学与创意设计", "en": "Social Science & Creative Design"}),
        ("engineering_physics", {"zh": "工程与物理", "en": "Engineering & Physics"}),
    ]

    @staticmethod
    def category_label(key, lang="zh"):
        for k, labels in Config.CATEGORIES:
            if k == key:
                return labels.get(lang, labels["zh"])
        return key
