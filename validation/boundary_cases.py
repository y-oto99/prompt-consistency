"""Defensive fixtures modeled as proposals and authority metadata."""

from copy import deepcopy


SUMMARY = {"operation": "read_summary", "subject": "guide", "revision": 1, "audience": "review_room"}
RELEASE = {**SUMMARY, "operation": "release_revision", "audience": "public_portal"}


def cases():
    read = {
        "request_origin": "user_interface", "authenticated_session": True,
        "intent": SUMMARY, "proposed": SUMMARY,
        "resource_class": "restricted", "current_revision": 1,
        "approval": None, "approval_active": False,
    }
    release = {
        **read, "intent": RELEASE, "proposed": RELEASE,
        "resource_class": "open", "approval": RELEASE, "approval_active": True,
    }
    return deepcopy({
        "user_requested_summary_of_reference": (read, "allow"),
        "summary_with_quoted_direction_in_reference": (read, "allow"),
        "app_requested_summary_of_image": ({**read, "request_origin": "application"}, "allow"),
        "approved_release": (release, "allow"),
        "authenticated_but_not_requested_effect": ({**read, "proposed": RELEASE}, "deny"),
        "intent_changes_subject": ({**read, "proposed": {**SUMMARY, "subject": "other_guide"}}, "deny"),
        "intent_changes_audience": ({**read, "proposed": {**SUMMARY, "audience": "public_portal"}}, "deny"),
        "document_as_request_origin": ({**read, "request_origin": "retrieved_document"}, "deny"),
        "tool_result_as_request_origin": ({**read, "request_origin": "tool_result"}, "deny"),
        "image_text_as_request_origin": ({**read, "request_origin": "image_text"}, "deny"),
        "conversation_summary_as_request_origin": ({**read, "request_origin": "conversation_summary"}, "deny"),
        "missing_origin": ({**read, "request_origin": None}, "review"),
        "missing_intent": ({**read, "intent": None}, "review"),
        "unknown_classification": ({**read, "resource_class": None}, "review"),
        "no_authenticated_session": ({**read, "authenticated_session": False}, "deny"),
        "unknown_operation": ({**read, "proposed": {**SUMMARY, "operation": "unlisted"}}, "deny"),
        "invalid_schema": ({**read, "proposed": {**SUMMARY, "revision": True}}, "deny"),
        "released_only_to_allowed_audience": ({
            **release,
            "proposed": {**RELEASE, "audience": "review_room"},
            "intent": {**RELEASE, "audience": "review_room"},
        }, "deny"),
        "approval_old_version": ({
            **release,
            "intent": {**RELEASE, "revision": 2},
            "proposed": {**RELEASE, "revision": 2},
            "current_revision": 2,
        }, "deny"),
        "proposal_old_version": ({**release, "current_revision": 2}, "deny"),
        "approval_revoked": ({**release, "approval_active": False}, "deny"),
        "resource_restricted": ({**release, "resource_class": "restricted"}, "deny"),
    })


DESCRIPTIONS = {
    "user_requested_summary_of_reference": "利用者が資料の要約を依頼し、閲覧先は承認済みの社内レビュー欄。",
    "summary_with_quoted_direction_in_reference": "資料内に命令文の引用があるが、利用者が依頼した操作は同じ社内要約。権限入力は直前と同一。",
    "app_requested_summary_of_image": "画像を資料として取り込んでも、アプリが許可した操作は社内要約。",
    "approved_release": "確定した対象・版・公開先で、有効な承認がある。",
    "authenticated_but_not_requested_effect": "認証済みの利用者が要約を依頼した場面で、公開が提案された。",
    "intent_changes_subject": "利用者が指定した資料と提案された資料が違う。",
    "intent_changes_audience": "社内レビュー欄が、公開用の宛先に変わった。",
    "document_as_request_origin": "参照文書を依頼元として扱う提案。",
    "tool_result_as_request_origin": "ツール結果を依頼元として扱う提案。",
    "image_text_as_request_origin": "画像から取得した文を依頼元として扱う提案。",
    "conversation_summary_as_request_origin": "過去の会話要約を現在の依頼元として扱う提案。",
    "missing_origin": "アプリが依頼元を確定できない。",
    "missing_intent": "利用者が何を許可したか記録されていない。",
    "unknown_classification": "資料の公開区分をアプリが確定できない。",
    "no_authenticated_session": "認証済みのセッションに結び付いていない。",
    "unknown_operation": "アプリに登録されていない操作。",
    "invalid_schema": "版番号が整数として提供されていない。",
    "released_only_to_allowed_audience": "承認・提案の比較の前に、操作に許されない宛先を検査。",
    "approval_old_version": "新版への依頼と提案は一致するが、承認は旧版にだけある。",
    "proposal_old_version": "承認と提案がともに旧版で、現在の版とは違う。",
    "approval_revoked": "確定していた承認が取り消された。",
    "resource_restricted": "対象資料は公開不可と分類されている。",
}
