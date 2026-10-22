<?php

declare(strict_types=1);

namespace Drupal\farm_quick_group\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\farm_quick\Plugin\Action\QuickFormActionBase;

/**
 * Action for recording group membership assignment.
 */
#[Action(
  id: 'quick_group',
  label: new TranslatableMarkup('Assign group membership'),
  confirm_form_route_name: 'farm.quick.group',
  type: 'asset',
)]
class Group extends QuickFormActionBase {

  /**
   * {@inheritdoc}
   */
  public function getQuickFormId(): string {
    return 'group';
  }

}
