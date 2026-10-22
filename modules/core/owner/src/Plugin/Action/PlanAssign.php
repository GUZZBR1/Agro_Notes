<?php

declare(strict_types=1);

namespace Drupal\farm_owner\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * Action that assigns users to plans.
 */
#[Action(
  id: 'plan_assign_action',
  label: new TranslatableMarkup('Assign plans to users.'),
  confirm_form_route_name: 'farm_owner.plan_assign_action_form',
  type: 'plan',
)]
class PlanAssign extends AssignBase {

}
