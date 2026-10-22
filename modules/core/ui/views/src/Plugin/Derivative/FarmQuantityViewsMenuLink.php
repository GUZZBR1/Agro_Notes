<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Plugin\Derivative;

/**
 * Provides menu links for farmOS Quantity Views.
 */
class FarmQuantityViewsMenuLink extends FarmViewsMenuLink {

  /**
   * {@inheritdoc}
   */
  protected string $entityType = 'quantity';

  /**
   * {@inheritdoc}
   */
  protected string $viewId = 'farm_log_quantity';

}
