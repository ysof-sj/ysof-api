from fastapi import Depends, BackgroundTasks
from bson import ObjectId
from app.shared import request_object, response_object, use_case
from app.infra.absent.absent_repository import AbsentRepository
from app.models.absent import AbsentModel
from app.models.student import StudentModel
from app.infra.manage_form.manage_form_repository import ManageFormRepository
from app.models.manage_form import ManageFormModel
from app.domain.manage_form.enum import FormStatus, FormType
from app.shared.utils.general import get_current_season_value
from app.models.subject import SubjectModel
from app.domain.manage_form.entity import ManageFormEvaluationOrAbsent
from app.infra.subject.subject_repository import SubjectRepository
from app.infra.student.student_repository import StudentRepository
from app.models.admin import AdminModel
from app.domain.audit_log.entity import AuditLogInDB
from app.domain.audit_log.enum import AuditLogType, Endpoint
import json
from app.infra.audit_log.audit_log_repository import AuditLogRepository


class DeleteAbsentRequestObject(request_object.ValidRequestObject):
    def __init__(
        self,
        subject_id: str,
        current_student: StudentModel | str,
        current_admin: AdminModel | None = None,
    ):
        self.subject_id = subject_id
        self.current_student = current_student
        self.current_admin = current_admin

    @classmethod
    def builder(
        cls,
        subject_id: str,
        current_student: StudentModel | str,
        current_admin: AdminModel | None = None,
    ) -> request_object.RequestObject:
        invalid_req = request_object.InvalidRequestObject()
        if subject_id is None:
            invalid_req.add_error("subject_id", "Invalid subject_id")

        if isinstance(current_student, str) and current_admin is None:
            invalid_req.add_error("current_admin", "Current admin is required")

        if invalid_req.has_errors():
            return invalid_req

        return DeleteAbsentRequestObject(
            subject_id=subject_id, current_student=current_student, current_admin=current_admin
        )


class DeleteAbsentUseCase(use_case.UseCase):
    def __init__(
        self,
        background_tasks: BackgroundTasks,
        audit_log_repository: AuditLogRepository = Depends(AuditLogRepository),
        manage_form_repository: ManageFormRepository = Depends(ManageFormRepository),
        subject_repository: SubjectRepository = Depends(SubjectRepository),
        student_repository: StudentRepository = Depends(StudentRepository),
        absent_repository: AbsentRepository = Depends(AbsentRepository),
    ):
        self.absent_repository = absent_repository
        self.manage_form_repository = manage_form_repository
        self.subject_repository = subject_repository
        self.student_repository = student_repository
        self.background_tasks = background_tasks
        self.audit_log_repository = audit_log_repository

    def process_request(self, req_object: DeleteAbsentRequestObject):
        is_student_request = True
        if isinstance(req_object.current_student, str):
            is_student_request = False
            student = self.student_repository.get_by_id(req_object.current_student)
            if not student:
                return response_object.ResponseFailure.build_not_found_error(
                    message="Học viên không tồn tại"
                )
            req_object.current_student = student

        absent: AbsentModel = self.absent_repository.find_one(
            {"student": req_object.current_student.id, "subject": ObjectId(req_object.subject_id)}
        )
        if not absent:
            return response_object.ResponseFailure.build_not_found_error(
                message="Đơn nghỉ phép không tồn tại"
            )

        current_season: int = get_current_season_value()
        subject: SubjectModel | None = self.subject_repository.get_by_id(req_object.subject_id)
        if subject is None or subject.season != current_season:
            return response_object.ResponseFailure.build_not_found_error(
                message="Môn học không tồn tại hoặc thuộc mùa cũ."
            )

        if is_student_request:
            form_absent: ManageFormModel | None = self.manage_form_repository.find_one(
                {"type": FormType.SUBJECT_ABSENT}
            )
            if not form_absent or form_absent.status == FormStatus.INACTIVE:
                return response_object.ResponseFailure.build_parameters_error(
                    message="Form chưa được mở."
                )
            if form_absent.status == FormStatus.CLOSED:
                return response_object.ResponseFailure.build_parameters_error(
                    message="Form đã được đóng."
                )
            form_absent: ManageFormEvaluationOrAbsent = ManageFormEvaluationOrAbsent.model_validate(
                form_absent
            )
            if req_object.subject_id != form_absent.data.subject_id:
                return response_object.ResponseFailure.build_parameters_error(
                    message="Form hiện tại không mở cho môn học này."
                )

        try:
            self.absent_repository.delete(id=absent.id)
            if not is_student_request:
                self.background_tasks.add_task(
                    self.audit_log_repository.create,
                    AuditLogInDB(
                        type=AuditLogType.DELETE,
                        endpoint=Endpoint.ABSENT,
                        season=current_season,
                        author=req_object.current_admin,
                        author_email=req_object.current_admin.email,
                        author_name=req_object.current_admin.full_name,
                        author_roles=req_object.current_admin.roles,
                        description=json.dumps(
                            {
                                "student_id": req_object.current_student.id,
                                "subject_id": req_object.subject_id,
                            },
                            default=str,
                            ensure_ascii=False,
                        ),
                    ),
                )
            return {"success": True}
        except Exception:
            return response_object.ResponseFailure.build_system_error("Something went error.")
