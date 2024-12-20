"""Subject repository module"""

from typing import Optional, Dict, Union, List, Any
from mongoengine import QuerySet, DoesNotExist
from bson import ObjectId
import pymongo

from app.models.subject import SubjectModel
from app.domain.subject.entity import SubjectInDB, SubjectInUpdateTime


class SubjectRepository:
    def __init__(self):
        pass

    def create(self, subject: SubjectInDB) -> SubjectModel:
        """
        Create new subject in db
        :param subject:
        :return:
        """
        # create subject instance
        new_doc = SubjectModel(**subject.model_dump())
        # and save it to db
        new_doc.save()

        return new_doc

    def get_by_id(self, subject_id: Union[str, ObjectId]) -> Optional[SubjectModel]:
        """
        Get subject in db from id
        :param subject_id:
        :return:
        """
        qs: QuerySet = SubjectModel.objects(id=subject_id)
        # retrieve unique result
        # https://mongoengine-odm.readthedocs.io/guide/querying.html#retrieving-unique-results
        try:
            subject: SubjectModel = qs.get()
            return subject
        except DoesNotExist:
            return None

    def update(self, id: ObjectId, data: Union[SubjectInUpdateTime, Dict[str, Any]]) -> bool:
        try:
            data = (
                data.model_dump(exclude_none=True)
                if isinstance(data, SubjectInUpdateTime)
                else data
            )
            SubjectModel.objects(id=id).update_one(**data, upsert=False)
            return True
        except Exception:
            return False

    def count(self, conditions: Dict[str, Union[str, bool, ObjectId]] = {}) -> int:
        try:
            return SubjectModel._get_collection().count_subjects(conditions)
        except Exception:
            return 0

    def list(
        self,
        page_index: int | None = 1,
        page_size: int | None = None,
        match_pipeline: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, int]] = None,
    ) -> List[SubjectModel]:
        pipeline = []
        if match_pipeline is not None:
            pipeline.append({"$match": match_pipeline})
        pipeline.append(
            {"$sort": sort if sort else {"created_at": -1}},
        )
        if page_size:
            pipeline.extend(
                [
                    {"$skip": page_size * (page_index - 1)},
                    {"$limit": page_size},
                ]
            )
        try:
            docs = SubjectModel.objects().aggregate(pipeline)
            return [SubjectModel.from_mongo(doc) for doc in docs] if docs else []
        except Exception:
            return []

    def count_list(
        self,
        match_pipeline: Optional[Dict[str, Any]] = None,
    ) -> int:
        pipeline = []

        if match_pipeline is not None:
            pipeline.append({"$match": match_pipeline})
        pipeline.append({"$count": "subject_count"})

        try:
            docs = SubjectModel.objects().aggregate(pipeline)
            return list(docs)[0]["subject_count"]
        except Exception:
            return 0

    def delete(self, id: ObjectId) -> bool:
        try:
            SubjectModel.objects(id=id).delete()
            return True
        except Exception:
            return False

    def find_one(self, conditions: Dict[str, Union[str, bool, ObjectId]]) -> Optional[SubjectModel]:
        try:
            doc = SubjectModel._get_collection().find_one(conditions)
            return SubjectModel.from_mongo(doc) if doc else None
        except Exception:
            return None

    def find(
        self, conditions: Dict[str, Union[str, bool, ObjectId]]
    ) -> List[Optional[SubjectModel]]:
        try:
            docs = SubjectModel._get_collection().find(conditions)
            return [SubjectModel.from_mongo(doc) for doc in docs] if docs else []
        except Exception:
            return []

    def bulk_update(
        self, data: Union[SubjectInUpdateTime, Dict[str, Any]], entities: List[SubjectModel]
    ) -> bool:
        try:
            if len(entities) == 0:
                return False

            data = (
                data.model_dump(exclude_none=True, exclude_unset=True)
                if isinstance(data, SubjectInUpdateTime)
                else data
            )
            operations = [
                pymongo.UpdateOne(
                    {"_id": season.id},
                    {"$set": data},
                    upsert=False,
                )
                for season in entities
            ]
            SubjectModel._get_collection().bulk_write(operations)
            return True
        except Exception:
            return False
