from typing import Optional, List
from fastapi import Depends
from app.shared import request_object, response_object, use_case
from app.domain.subject.entity import SubjectInDB, SubjectInStudent
from app.models.subject import SubjectModel
from app.infra.subject.subject_repository import SubjectRepository
from app.domain.lecturer.entity import LecturerInDB, LecturerInStudent
from app.models.student import StudentModel
from app.domain.document.entity import DocumentInDB, DocumentInStudent
from app.domain.subject.enum import StatusSubjectEnum


class ListSubjectsStudentRequestObject(request_object.ValidRequestObject):
    def __init__(
        self,
        current_student: StudentModel,
        search: Optional[str] = None,
        subdivision: Optional[str] = None,
        status: Optional[list[StatusSubjectEnum]] = None,
        sort: Optional[dict[str, int]] = None,
        season: Optional[int] = None,
    ):
        self.search = search
        self.sort = sort
        self.subdivision = subdivision
        self.current_student = current_student
        self.status = status
        self.season = season

    @classmethod
    def builder(
        cls,
        current_student: StudentModel,
        search: Optional[str] = None,
        subdivision: Optional[str] = None,
        status: Optional[list[StatusSubjectEnum]] = None,
        sort: Optional[dict[str, int]] = None,
        season: Optional[int] = None,
    ):
        return ListSubjectsStudentRequestObject(
            search=search,
            sort=sort,
            subdivision=subdivision,
            current_student=current_student,
            status=status,
            season=season,
        )


class ListSubjectsStudentUseCase(use_case.UseCase):
    def __init__(self, subject_repository: SubjectRepository = Depends(SubjectRepository)):
        self.subject_repository = subject_repository

    def process_request(self, req_object: ListSubjectsStudentRequestObject):
        if req_object.season:
            exists = any(
                season.season == req_object.season
                for season in req_object.current_student.seasons_info
            )
            if exists:
                match_pipeline = {"season": req_object.season}

            else:
                return response_object.ResponseFailure.build_parameters_error(
                    "Bạn không có quyền truy cập."
                )
        else:
            match_pipeline = {"season": req_object.current_student.seasons_info[-1].season}

        if isinstance(req_object.search, str):
            match_pipeline = {
                **match_pipeline,
                "$or": [
                    {"title": {"$regex": req_object.search, "$options": "i"}},
                    {"code": {"$regex": req_object.search, "$options": "i"}},
                ],
            }
        if isinstance(req_object.subdivision, str):
            match_pipeline = {**match_pipeline, "subdivision": req_object.subdivision}
        if isinstance(req_object.status, list):
            match_pipeline = {**match_pipeline, "status": {"$in": req_object.status}}

        subjects: List[SubjectModel] = self.subject_repository.list(
            sort=req_object.sort, match_pipeline=match_pipeline
        )

        return [
            SubjectInStudent(
                **SubjectInDB.model_validate(subject).model_dump(
                    exclude=({"lecturer", "attachments"})
                ),
                lecturer=LecturerInStudent(
                    **LecturerInDB.model_validate(subject.lecturer).model_dump()
                ),
                attachments=[
                    DocumentInStudent(
                        **DocumentInDB.model_validate(doc).model_dump(exclude=({"author"}))
                    )
                    for doc in subject.attachments
                ],
            )
            for subject in subjects
        ]
