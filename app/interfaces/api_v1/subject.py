from app.shared import response_object
from fastapi import APIRouter, Body, Depends,  Query, HTTPException, Path
from typing import Optional

from app.domain.subject.entity import Subject, SubjectInCreate, SubjectInUpdate
from app.domain.shared.enum import AdminRole, Sort
from app.infra.security.security_service import authorization, get_current_active_admin
from app.shared.decorator import response_decorator
from app.use_cases.subject.list import ListSubjectsUseCase, ListSubjectsRequestObject
from app.use_cases.subject.update import UpdateSubjectUseCase, UpdateSubjectRequestObject
from app.use_cases.subject.get import (
    GetSubjectRequestObject,
    GetSubjectCase,
)
from app.use_cases.subject.create import (
    CreateSubjectRequestObject,
    CreateSubjectUseCase,
)
from app.models.admin import AdminModel
from app.shared.constant import SUPER_ADMIN
from app.use_cases.subject.delete import DeleteSubjectRequestObject, DeleteSubjectUseCase

router = APIRouter()


@router.get(
    "/{subject_id}",
    dependencies=[Depends(get_current_active_admin)],
    response_model=Subject,
)
@response_decorator()
def get_subject_by_id(
        subject_id: str = Path(..., title="Subject id"),
        get_subject_use_case: GetSubjectCase = Depends(GetSubjectCase),
):
    get_subject_request_object = GetSubjectRequestObject.builder(
        subject_id=subject_id)
    response = get_subject_use_case.execute(
        request_object=get_subject_request_object)
    return response


@router.post(
    "",
    response_model=Subject,
)
@response_decorator()
def create_subject(
        payload: SubjectInCreate = Body(...,
                                        title="Subject In Create payload"),
        create_subject_use_case: CreateSubjectUseCase = Depends(
            CreateSubjectUseCase),
        current_admin: AdminModel = Depends(get_current_active_admin),
):
    authorization(current_admin, [*SUPER_ADMIN, AdminRole.BHV])
    req_object = CreateSubjectRequestObject.builder(payload=payload)
    response = create_subject_use_case.execute(request_object=req_object)
    return response


@router.get(
    "",
    response_model=list[Subject],
    dependencies=[Depends(get_current_active_admin)]
)
@response_decorator()
def get_list_subjects(
        list_subjects_use_case: ListSubjectsUseCase = Depends(
            ListSubjectsUseCase),
        search: Optional[str] = Query(None, title="Search"),
        sort: Optional[Sort] = Sort.DESC,
        sort_by: Optional[str] = 'id',
):
    annotations = {}
    for base in reversed(Subject.__mro__):
        annotations.update(getattr(base, '__annotations__', {}))
    if sort_by not in annotations:
        raise HTTPException(
            status_code=400, detail=f"Invalid sort_by: {sort_by}")
    sort_query = {sort_by: 1 if sort is sort.ASCE else -1}

    req_object = ListSubjectsRequestObject.builder(
        search=search,
        sort=sort_query)
    response = list_subjects_use_case.execute(request_object=req_object)
    return response


@router.put(
    "/{id}",
    response_model=Subject,
)
@response_decorator()
def update_subject(
        id: str = Path(..., title="Subject Id"),
        payload: SubjectInUpdate = Body(...,
                                        title="Subject updated payload"),
        update_subject_use_case: UpdateSubjectUseCase = Depends(
            UpdateSubjectUseCase),
        current_admin: AdminModel = Depends(get_current_active_admin),
):
    authorization(current_admin, [*SUPER_ADMIN, AdminRole.BHV, AdminRole.BKT])
    if AdminRole.BKT in current_admin.roles and AdminRole.BHV not in current_admin.roles:
        print("11111111111111111")
        if payload.zoom is None:
            return response_object.ResponseFailure.build_parameters_error(
                message="Vui lòng điền thông tin zoom"
            )
        payload = SubjectInUpdate(zoom=payload.zoom)
    req_object = UpdateSubjectRequestObject.builder(id=id, payload=payload)
    response = update_subject_use_case.execute(request_object=req_object)
    return response


@router.delete("/{id}")
@response_decorator()
def delete_subject(
        id: str = Path(..., title="Subject Id"),
        delete_subject_use_case: DeleteSubjectUseCase = Depends(
            DeleteSubjectUseCase),
        current_admin: AdminModel = Depends(get_current_active_admin),
):
    authorization(current_admin, [*SUPER_ADMIN, AdminRole.BHV])
    req_object = DeleteSubjectRequestObject.builder(id=id)
    response = delete_subject_use_case.execute(request_object=req_object)
    return response