<?php

declare(strict_types=1);

namespace Drupal\farm_quick;

use Drupal\Component\Plugin\Exception\PluginException;
use Drupal\Component\Plugin\PluginManagerInterface;
use Drupal\Core\Plugin\DefaultSingleLazyPluginCollection;

/**
 * Provides a collection of quick form plugins.
 */
class QuickFormPluginCollection extends DefaultSingleLazyPluginCollection {

  public function __construct(
    PluginManagerInterface $manager,
    $instance_id,
    array $configuration,
    protected ?string $quickFormId = NULL,
  ) {
    parent::__construct($manager, $instance_id, $configuration);
  }

  /**
   * {@inheritdoc}
   */
  protected function initializePlugin($instance_id) {
    if (!$instance_id) {
      throw new PluginException("The quick form '{$this->quickFormId}' did not specify a plugin.");
    }
    parent::initializePlugin($instance_id);
  }

}
