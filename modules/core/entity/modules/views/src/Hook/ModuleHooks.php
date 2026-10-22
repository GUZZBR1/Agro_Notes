<?php

declare(strict_types=1);

namespace Drupal\farm_entity_views\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Hook\Order\OrderAfter;
use Drupal\views\ViewsData;

/**
 * Module hook implementations for farm_entity_views.
 */
class ModuleHooks {

  public function __construct(
    protected ViewsData $viewsData,
  ) {}

  /**
   * Implements hook_modules_installed().
   *
   * Make sure this module's implementation runs after that of the entity
   * module, so that we rebuild views data after bundle fields are installed.
   */
  #[Hook('modules_installed', order: new OrderAfter(['entity']))]
  public function modulesInstalled($modules, $is_syncing) {

    // Reset the views data after installing modules.
    // See https://www.drupal.org/project/entity/issues/3206703#comment-14073184
    $this->viewsData->clear();
  }

}
