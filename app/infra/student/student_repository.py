"""Student repository module"""

from typing import Optional, Dict, Union, List, Any
from mongoengine import QuerySet, DoesNotExist
from bson import ObjectId

from app.models.student import StudentModel
from app.domain.student.entity import StudentInDB, StudentInUpdate


class StudentRepository:
    def __init__(self):
        pass

    def create(self, student: StudentInDB) -> StudentInDB:
        """
        Create new student in db
        :param student:
        :return:
        """
        # create student document instance
        new_student = StudentModel(**student.model_dump())
        # and save it to db
        new_student.save()

        return StudentInDB.model_validate(new_student)

    def get_by_id(self, student_id: Union[str, ObjectId]) -> Optional[StudentModel]:
        """
        Get student in db from id
        :param student_id:
        :return:
        """
        qs: QuerySet = StudentModel.objects(id=student_id)
        # retrieve unique result
        # https://mongoengine-odm.readthedocs.io/guide/querying.html#retrieving-unique-results
        try:
            student: StudentModel = qs.get()
            return student
        except DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[StudentModel]:
        """
        Get student in db from email
        :param student_email:
        :return:
        """
        qs: QuerySet = StudentModel.objects(email=email)
        # retrieve unique result
        # https://mongoengine-odm.readthedocs.io/guide/querying.html#retrieving-unique-results
        try:
            student = qs.get()
        except DoesNotExist:
            return None
        return student

    def update(self, id: ObjectId, data: Union[StudentInUpdate, Dict[str, Any]]) -> bool:
        try:
            data = data.model_dump(exclude_none=True) if isinstance(data, StudentInUpdate) else data
            StudentModel.objects(id=id).update_one(**data, upsert=False)
            return True
        except Exception:
            return False

    def count(self, conditions: Dict[str, Union[str, bool, ObjectId]] = {}) -> int:
        try:
            return StudentModel._get_collection().count_documents(conditions)
        except Exception:
            return 0

    def list(
        self,
        page_index: int = 1,
        page_size: int = 20,
        match_pipeline: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = None,
    ) -> List[StudentModel]:
        pipeline = [
            {"$sort": sort if sort else {"created_at": -1}},
            {"$skip": page_size * (page_index - 1)},
            {"$limit": page_size},
        ]

        if match_pipeline is not None:
            pipeline.append({"$match": match_pipeline})

        try:
            docs = StudentModel.objects().aggregate(pipeline)
            return [StudentModel.from_mongo(doc) for doc in docs] if docs else []
        except Exception:
            return []

    def count_list(
        self,
        match_pipeline: Optional[Dict[str, Any]] = None,
    ) -> int:
        pipeline = []

        if match_pipeline is not None:
            pipeline.append({"$match": match_pipeline})
        pipeline.append({"$count": "document_count"})

        try:
            docs = StudentModel.objects().aggregate(pipeline)
            return list(docs)[0]["document_count"]
        except Exception:
            return 0

    def delete(self, id: ObjectId) -> bool:
        try:
            StudentModel.objects(id=id).delete()
            return True
        except Exception:
            return False

    def find_one(self, conditions: Dict[str, Union[str, bool, ObjectId]]) -> Optional[StudentModel]:
        try:
            doc = StudentModel._get_collection().find_one(conditions)
            return StudentModel.from_mongo(doc) if doc else None
        except Exception:
            return None