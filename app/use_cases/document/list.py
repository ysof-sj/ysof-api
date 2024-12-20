import math
from typing import Optional, List, Any
from fastapi import Depends
from app.shared import request_object, use_case, response_object
from app.domain.document.entity import (
    AdminInDocument,
    Document,
    DocumentInDB,
    ManyDocumentsInResponse,
)
from app.domain.shared.entity import Pagination
from app.models.document import DocumentModel
from app.infra.document.document_repository import DocumentRepository
from app.models.admin import AdminModel
from app.domain.document.enum import DocumentType
from app.domain.admin.entity import AdminInDB
from app.shared.constant import SUPER_ADMIN
from app.domain.shared.enum import AdminRole
from app.shared.utils.general import get_current_season_value


class ListDocumentsRequestObject(request_object.ValidRequestObject):
    def __init__(
        self,
        current_admin: AdminModel,
        page_index: int,
        page_size: int,
        search: Optional[str] = None,
        label: Optional[list[str]] = None,
        sort: Optional[dict[str, int]] = None,
        season: int | None = None,
        type: Optional[DocumentType] = None,
        roles: Optional[list[str]] = None,
    ):
        self.page_index = page_index
        self.page_size = page_size
        self.search = search
        self.sort = sort
        self.label = label
        self.current_admin = current_admin
        self.roles = roles
        self.season = season
        self.type = type

    @classmethod
    def builder(
        cls,
        current_admin: AdminModel,
        page_index: int,
        page_size: int,
        search: Optional[str] = None,
        label: Optional[list[str]] = None,
        sort: Optional[dict[str, int]] = None,
        season: int | None = None,
        type: Optional[DocumentType] = None,
        roles: Optional[list[str]] = None,
    ):
        return ListDocumentsRequestObject(
            current_admin=current_admin,
            page_index=page_index,
            label=label,
            page_size=page_size,
            search=search,
            sort=sort,
            season=season,
            type=type,
            roles=roles,
        )


class ListDocumentsUseCase(use_case.UseCase):
    def __init__(self, document_repository: DocumentRepository = Depends(DocumentRepository)):
        self.document_repository = document_repository

    def match_pipeline_helper(
        self,
        req_object: ListDocumentsRequestObject,
    ):
        """_summary_

        Args:
            req_object : ListDocumentsRequestObject

        Returns:
            dict[str, Any]:
                A MongoDB match pipeline dictionary for filtering documents based on the
                provided criteria.
            ResponseFailure:
                If the admin lacks permissions to access the requested season or type, a
                `ResponseFailure` object is returned with an appropriate error message.

        Logic:
            1. Type student is separated when get all
            2. With super admin, can get specific any season, any type. With no season
               in query parameter, auto get current season
               if season == 0, return all documents
            3. With other admin,
                - With no season in query parameter, get last season of admin
                    - Type annual: <= season selected
                    - Type common = season selected
                    - Type internal = season selected with role in roles of admin

        """
        current_season = get_current_season_value()

        match_pipeline: dict[str, Any] | None = {}
        is_super_admin = AdminInDB.model_validate(req_object.current_admin).active() and any(
            role in SUPER_ADMIN for role in req_object.current_admin.roles
        )
        # if season in query is None, then get season_default
        season_default = (
            req_object.current_admin.latest_season
            if AdminRole.ADMIN not in req_object.current_admin.roles
            else current_season
        )

        if not is_super_admin and req_object.season == 0:
            return response_object.ResponseFailure.build_parameters_error(
                "Bạn không có quyền truy cập tất cả mùa"
            )

        if isinstance(req_object.type, str):
            match_pipeline = {**match_pipeline, "type": req_object.type}

        if req_object.type == DocumentType.STUDENT:
            if is_super_admin and req_object.season == 0:
                return match_pipeline
            if (
                is_super_admin
                or (
                    isinstance(req_object.season, int)
                    and req_object.season <= req_object.current_admin.latest_season
                )
                or req_object.season is None
            ):
                return {
                    **match_pipeline,
                    "season": (
                        req_object.season
                        if req_object.season
                        and (
                            req_object.season <= req_object.current_admin.latest_season
                            or is_super_admin
                        )
                        else season_default
                    ),
                }

            return response_object.ResponseFailure.build_parameters_error(
                "Bạn không có quyền truy cập " + (f"mùa {req_object.season}")
            )

        if is_super_admin and req_object.season == 0:
            return match_pipeline

        if (
            is_super_admin
            or (
                isinstance(req_object.season, int)
                and req_object.season <= req_object.current_admin.latest_season
            )
            or req_object.season is None
        ):
            match_pipeline = {
                **match_pipeline,
                "$or": [
                    {
                        "$and": [
                            {"type": DocumentType.ANNUAL},
                            {
                                "season": {
                                    "$lte": (
                                        req_object.season
                                        if req_object.season
                                        and (
                                            req_object.season
                                            <= req_object.current_admin.latest_season
                                            or is_super_admin
                                        )
                                        else season_default
                                    )
                                }
                            },
                        ]
                    },
                    {
                        "$and": [
                            {
                                "$or": [
                                    {"type": DocumentType.COMMON},
                                    (
                                        {"type": DocumentType.INTERNAL}
                                        if is_super_admin
                                        else {
                                            "$and": [
                                                {"type": DocumentType.INTERNAL},
                                                {"role": {"$in": req_object.current_admin.roles}},
                                            ]
                                        }
                                    ),
                                ]
                            },
                            {
                                "season": (
                                    req_object.season if req_object.season else season_default
                                )
                            },
                        ]
                    },
                ],
            }
            return match_pipeline

        return response_object.ResponseFailure.build_parameters_error(
            "Bạn không có quyền truy cập " + (f"mùa {req_object.season}")
        )

    def process_request(self, req_object: ListDocumentsRequestObject):
        match_pipeline = self.match_pipeline_helper(
            req_object=req_object,
        )

        if isinstance(match_pipeline, response_object.ResponseFailure):
            return match_pipeline

        if isinstance(req_object.search, str):
            match_pipeline = {
                **match_pipeline,
                "name": {"$regex": req_object.search, "$options": "i"},
            }

        if isinstance(req_object.label, list) and len(req_object.label) > 0:
            match_pipeline = {**match_pipeline, "label": {"$in": req_object.label}}

        if isinstance(req_object.roles, list) and len(req_object.roles) > 0:
            match_pipeline = {**match_pipeline, "role": {"$in": req_object.roles}}

        documents: List[DocumentModel] = self.document_repository.list(
            page_size=req_object.page_size,
            page_index=req_object.page_index,
            sort=req_object.sort,
            match_pipeline=match_pipeline,
        )

        total = self.document_repository.count_list(match_pipeline=match_pipeline)

        data: Optional[list[Document]] = []
        for doc in documents:
            author: AdminInDB = AdminInDB.model_validate(doc.author)
            data.append(
                Document(
                    **DocumentInDB.model_validate(doc).model_dump(exclude=({"author"})),
                    author=AdminInDocument(**author.model_dump(), active=author.active()),
                )
            )

        return ManyDocumentsInResponse(
            pagination=Pagination(
                total=total,
                page_index=req_object.page_index,
                total_pages=math.ceil(total / req_object.page_size),
            ),
            data=data,
        )
