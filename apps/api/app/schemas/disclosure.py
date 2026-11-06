from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

EditingExtentType = Literal["none_or_minimal", "some_editing", "extensive_editing"]
CreationMethodType = Literal["ai_generated", "ai_assisted", "none"]


class AIDisclosureConfirmRequest(BaseModel):
    # Text Category
    text_creation_method: CreationMethodType
    text_tools_used: List[str] = Field(default_factory=list)
    text_editing_extent: Optional[EditingExtentType] = None

    # Image Category
    image_creation_method: CreationMethodType
    image_tools_used: List[str] = Field(default_factory=list)
    image_editing_extent: Optional[EditingExtentType] = None

    # Translation Category
    translation_creation_method: CreationMethodType
    translation_tools_used: List[str] = Field(default_factory=list)
    translation_editing_extent: Optional[EditingExtentType] = None

    # Mandatory Explicit Author Affirmation
    author_confirmed: bool = Field(..., description="Must explicitly be True.")

    @model_validator(mode="after")
    def validate_declarations(self) -> "AIDisclosureConfirmRequest":
        if not self.author_confirmed:
            raise ValueError("Author must explicitly confirm the disclosure (author_confirmed=True).")

        categories = [
            ("Text", self.text_creation_method, self.text_tools_used, self.text_editing_extent),
            ("Image", self.image_creation_method, self.image_tools_used, self.image_editing_extent),
            ("Translation", self.translation_creation_method, self.translation_tools_used, self.translation_editing_extent),
        ]

        for name, method, tools, extent in categories:
            if method == "ai_generated":
                if not tools:
                    raise ValueError(f"{name} is declared as 'ai_generated' but no AI tools were provided.")
                if not extent:
                    raise ValueError(f"{name} is declared as 'ai_generated' but editing extent was not provided.")
            elif method == "ai_assisted":
                if not tools:
                    raise ValueError(f"{name} is declared as 'ai_assisted' but brainstorming/editing tools were not provided.")
                if extent is not None:
                    raise ValueError(f"{name} is declared as 'ai_assisted', which does not collect editing extent.")
            elif method == "none":
                if tools:
                    raise ValueError(f"{name} is declared as 'none' but tools were listed.")
                if extent is not None:
                    raise ValueError(f"{name} is declared as 'none' but editing extent was provided.")

        return self


class AIDisclosureResponse(BaseModel):
    id: str
    user_id: str
    disclosure_version: str
    text_creation_method: str
    text_tools_used: List[str]
    text_editing_extent: Optional[str] = None
    image_creation_method: str
    image_tools_used: List[str]
    image_editing_extent: Optional[str] = None
    translation_creation_method: str
    translation_tools_used: List[str]
    translation_editing_extent: Optional[str] = None
    kdp_submission_declaration: str
    author_reviewed: bool
    author_attested_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
