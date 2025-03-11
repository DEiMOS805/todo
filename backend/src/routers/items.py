from sqlmodel import select
from typing import Any, Annotated, Sequence
from fastapi.responses import JSONResponse, Response
from fastapi import APIRouter, Query, Path, Body, Depends, HTTPException, status

from src.resources.models import ItemBase, Item, ItemUpdate, User
from src.resources.dependencies import SessionDep, get_current_active_user


router = APIRouter()


@router.post("/users/{user_id}/items", response_model=dict[str, Any])
async def create_item(
	user_id: Annotated[int, Path(gt=0)],
	current_user: Annotated[User, Depends(get_current_active_user)],
	session: SessionDep,
	item: ItemBase
) -> JSONResponse:

	if not current_user.is_admin and current_user.id != user_id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Given user does not have the necessary rights for this operation!"
		)

	ItemBase.model_validate(item)

	user_db: User | None = session.get(User, user_id)
	if not user_db:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User with id {user_id} not found!"
		)

	new_item: Item = Item(
		title=item.title,
		description=item.description,
		done=item.done,
		user_id=user_db.id
	)
	session.add(new_item)
	session.commit()
	session.refresh(new_item)

	return JSONResponse(
		status_code=status.HTTP_201_CREATED,
		content={
			"status": "Success",
			"message": "Item created successfully!",
			"item": new_item.model_dump(),
		}
	)


@router.get("/items", response_model=dict[str, Any])
async def get_items(
	current_user: Annotated[User, Depends(get_current_active_user)],
	session: SessionDep,
	offset: Annotated[int, Query(ge=0)] = 0,
	limit: Annotated[int, Query(ge=1)] = 10
) -> Response | JSONResponse:

	if not current_user.is_admin:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Given user does not have the necessary rights for this operation!"
		)

	items: Sequence[Item] = session.exec(
		select(Item).offset(offset).limit(limit)
	).all()
	if not items:
		return Response(status_code=status.HTTP_204_NO_CONTENT)

	items_list = list(map(lambda item: item.model_dump(), items))

	return JSONResponse(
		status_code=status.HTTP_200_OK,
		content={
			"status": "Success",
			"message": "Items retrieved successfully!",
			"items": items_list,
		}
	)


@router.get("/users/{user_id}/items", response_model=dict[str, Any])
async def get_user_items(
	user_id: Annotated[int, Path(gt=0)],
	current_user: Annotated[User, Depends(get_current_active_user)],
	session: SessionDep,
	offset: Annotated[int, Query(ge=0)] = 0,
	limit: Annotated[int, Query(ge=1)] = 10
) -> Response | JSONResponse:

	if not current_user.is_admin and current_user.id != user_id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Given user does not have the necessary rights for this operation!"
		)

	user: User | None = session.get(User, user_id)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User with id {user_id} not found!"
		)

	if not user.items:
		return Response(status_code=status.HTTP_204_NO_CONTENT)

	items: list[dict[str, Any]] = list(map(lambda item: item.model_dump(), user.items))
	items = items[offset:offset + limit]

	return JSONResponse(
		status_code=status.HTTP_200_OK,
		content={
			"status": "Success",
			"message": "Items retrieved successfully!",
			"items": items,
		}
	)


@router.get("/users/{user_id}/items/{item_id}", response_model=dict[str, Any])
async def get_item(
	user_id: Annotated[int, Path(gt=0)],
	item_id: Annotated[int, Path(gt=0)],
	current_user: Annotated[User, Depends(get_current_active_user)],
	session: SessionDep
) -> JSONResponse:

	if not current_user.is_admin and current_user.id != user_id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Given user does not have the necessary rights for this operation!"
		)

	user: User | None = session.get(User, user_id)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User with id {user_id} not found!"
		)

	item: Item | None = session.exec(select(Item). \
		where(Item.id == item_id).where(Item.user_id == user_id)
	).first()
	if not item:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Item with id {item_id} for user with id {user_id} not found!"
		)

	return JSONResponse(
		status_code=status.HTTP_200_OK,
		content={
			"status": "Success",
			"message": "Item retrieved successfully!",
			"item": item.model_dump(),
		}
	)


@router.patch("/users/{user_id}/items/{item_id}", response_model=dict[str, Any])
async def patch_item(
	user_id: Annotated[int, Path(gt=0)],
	item_id: Annotated[int, Path(gt=0)],
	session: SessionDep,
	current_user: Annotated[User, Depends(get_current_active_user)],
	item: Annotated[ItemUpdate, Body()]
) -> JSONResponse:

	if not current_user.is_admin and current_user.id != user_id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Given user does not have the necessary rights for this operation!"
		)

	user: User | None = session.get(User, user_id)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User with id {user_id} not found!"
		)

	item_db: Item | None = session.exec(select(Item). \
		where(Item.id == item_id).where(Item.user_id == user_id)
	).first()
	if not item_db:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Item with id {item_id} for user with id {user_id} not found!"
		)

	ItemUpdate.model_validate(item)

	if item.title:
		item_db.title = item.title
	if item.description:
		item_db.description = item.description
	if item.done is not None:
		item_db.done = item.done

	session.add(item_db)
	session.commit()
	session.refresh(item_db)

	return JSONResponse(
		status_code=status.HTTP_200_OK,
		content={
			"status": "Success",
			"message": "Item patched successfully!",
			"item": item_db.model_dump(),
		}
	)


@router.delete("/users/{user_id}/items/{item_id}", response_model=dict[str, Any])
async def delete_item(
	user_id: Annotated[int, Path(gt=0)],
	item_id: Annotated[int, Path(gt=0)],
	current_user: Annotated[User, Depends(get_current_active_user)],
	session: SessionDep
) -> JSONResponse:

	if not current_user.is_admin and current_user.id != user_id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Given user does not have the necessary rights for this operation!"
		)

	user: User | None = session.get(User, user_id)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"User with id {user_id} not found!"
		)

	item: Item | None = session.exec(select(Item). \
		where(Item.id == item_id).where(Item.user_id == user_id)
	).first()
	if not item:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=f"Item with id {item_id} for user with id {user_id} not found!"
		)

	session.delete(item)
	session.commit()

	return JSONResponse(
		status_code=status.HTTP_200_OK,
		content={
			"status": "Success",
			"message": "Item deleted successfully!"
		}
	)
