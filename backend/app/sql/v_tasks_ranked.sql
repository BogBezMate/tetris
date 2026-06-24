-- Представление с метриками. Логика 1:1 с n8n; считается на лету, в полях не хранится.
-- Применяется отдельной миграцией; TaskRanked читает отсюда.
DROP VIEW IF EXISTS v_tasks_ranked;
CREATE VIEW v_tasks_ranked AS
SELECT
    t.task_id,
    t.jira_key,
    t.jira_internal_id,
    t.task_summary,
    t.issue_type,
    t.task_status,
    t.business_unit,
    t.change_scope,
    t.customer_name,
    t.it_business_partner,
    t.dod_text,
    t.goal_type_id,
    gt.goal_type_name,
    t.company_effect_rub,
    t.eta_months,
    t.adjusted_ebitda,
    t.total_story_points,
    t.contractor_cost_rub,
    t.coefficient,
    t.ceo_priority,
    t.current_sprint,
    t.has_active_sprint,
    t.end_date,
    t.baseline_end_date,
    t.max_sprints_override,

    -- Метки одной строкой (как делал n8n: join через запятую).
    (SELECT string_agg(tl.label_name, ', ' ORDER BY tl.label_name)
     FROM task_labels tl WHERE tl.task_id = t.task_id) AS labels,

    -- Требуемые платформы одной строкой (поле Platform из Jira).
    (SELECT string_agg(p.platform_name, ', ' ORDER BY p.platform_name)
     FROM task_platforms tp JOIN platforms p ON p.platform_id = tp.platform_id
     WHERE tp.task_id = t.task_id AND tp.is_required = TRUE) AS platforms_required,

    -- Приведённый годовой эффект: только для целей с affects_effect и ненулевым ETA.
    CASE
        WHEN COALESCE(gt.affects_effect, FALSE) AND COALESCE(t.eta_months, 0) > 0
            THEN t.company_effect_rub / t.eta_months * 12
        ELSE 0
    END AS adjusted_annual_effect,

    -- По чему ранжируем: EBITDA на стори-поинт, иначе на стоимость подрядчиков.
    CASE
        WHEN COALESCE(t.total_story_points, 0) > 0
            THEN COALESCE(t.adjusted_ebitda, 0) / t.total_story_points
        WHEN COALESCE(t.contractor_cost_rub, 0) > 0
            THEN COALESCE(t.adjusted_ebitda, 0) / t.contractor_cost_rub
        ELSE 0
    END AS ebitda_per_story_point,

    -- 4 НЕПЕРЕСЕКАЮЩИХСЯ признака качества оценки (для фильтра/пометок).
    -- Базовые условия: есть выбранная платформа / есть хоть одна оценка.

    -- (1) Недооценена: есть ВЫБРАННАЯ платформа без оценки.
    EXISTS (
        SELECT 1 FROM task_platforms tp
        WHERE tp.task_id = t.task_id
          AND tp.is_required = TRUE
          AND COALESCE(tp.estimate_story_points, 0) = 0
    ) AS is_underestimated,

    -- (2) Без платформ (пусто): нет выбранных платформ И нет ни одной оценки.
    (NOT EXISTS (SELECT 1 FROM task_platforms tp
                 WHERE tp.task_id = t.task_id AND tp.is_required = TRUE)
     AND NOT EXISTS (SELECT 1 FROM task_platforms tp
                     WHERE tp.task_id = t.task_id AND COALESCE(tp.estimate_story_points, 0) > 0)
    ) AS is_unplatformed,

    -- (3) Оценка есть, команда не выбрана: нет выбранных платформ, НО есть оценка.
    (NOT EXISTS (SELECT 1 FROM task_platforms tp
                 WHERE tp.task_id = t.task_id AND tp.is_required = TRUE)
     AND EXISTS (SELECT 1 FROM task_platforms tp
                 WHERE tp.task_id = t.task_id AND COALESCE(tp.estimate_story_points, 0) > 0)
    ) AS has_estimate_no_team,

    -- (4) Оценка у невыбранной платформы (смешанный): есть выбранные платформы
    -- И при этом оценка стоит у НЕвыбранной.
    (EXISTS (SELECT 1 FROM task_platforms tp
             WHERE tp.task_id = t.task_id AND tp.is_required = TRUE)
     AND EXISTS (SELECT 1 FROM task_platforms tp
                 WHERE tp.task_id = t.task_id AND tp.is_required = FALSE
                   AND COALESCE(tp.estimate_story_points, 0) > 0)
    ) AS has_unselected_estimate,

    -- МАКСИМУМ спринтов (как в Excel: ROUNDUP(MAX(оценка_платформы / velocity_платформы))).
    -- Если задан ручной max_sprints_override (>0) — берём его, иначе считаем автоматически.
    COALESCE(
        NULLIF(t.max_sprints_override, 0),
        (SELECT CEIL(MAX(tp.estimate_story_points / NULLIF(p.sp_per_sprint, 0)))
           FROM task_platforms tp
           JOIN platforms p ON p.platform_id = tp.platform_id
          WHERE tp.task_id = t.task_id),
        0
    ) AS max_sprints

FROM tasks t
LEFT JOIN goal_types gt ON gt.goal_type_id = t.goal_type_id;
