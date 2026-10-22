<?php

declare(strict_types=1);

namespace Drupal\data_stream\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\data_stream\DataStreamTypeManager;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Views hook implementations for data_stream.
 */
class ViewsHooks {

  public function __construct(
    #[Autowire(service: 'plugin.manager.data_stream_type')]
    protected DataStreamTypeManager $dataStreamTypeManager,
  ) {}

  /**
   * Implements hook_views_data().
   */
  #[Hook('views_data')]
  public function viewsData() {
    $data = [];

    // Collect views data from all data stream type plugins.
    $data_stream_types = $this->dataStreamTypeManager->getDefinitions();
    foreach (array_keys($data_stream_types) as $plugin_id) {
      /** @var \Drupal\data_stream\Plugin\DataStream\DataStreamType\DataStreamTypeInterface $plugin */
      $plugin = $this->dataStreamTypeManager->createInstance($plugin_id);
      $data = array_replace_recursive($data, $plugin->getViewsData());
    }

    return $data;
  }

}
