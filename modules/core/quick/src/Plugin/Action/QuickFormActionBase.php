<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Plugin\Action;

use Drupal\Core\Action\Plugin\Action\EntityActionBase;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\TempStore\PrivateTempStoreFactory;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Base class for quick form action plugins.
 */
abstract class QuickFormActionBase extends EntityActionBase {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    EntityTypeManagerInterface $entity_type_manager,
    protected PrivateTempStoreFactory $tempStoreFactory,
    protected AccountInterface $currentUser,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition, $entity_type_manager);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    // @todo Use autowiring and remove this when the parent class does.
    // @see https://www.drupal.org/project/drupal/issues/3552110
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('entity_type.manager'),
      $container->get('tempstore.private'),
      $container->get('current_user')
    );
  }

  /**
   * Get the quick form ID the action is associated with.
   *
   * @return string
   *   The quick form ID.
   */
  abstract public function getQuickFormId(): string;

  /**
   * {@inheritdoc}
   */
  public function executeMultiple(array $entities) {
    /** @var \Drupal\Core\Entity\EntityInterface[] $entities */
    $this->tempStoreFactory->get('farm_quick.' . $this->getQuickFormId())->set($this->currentUser->id() . ':' . $this->getPluginDefinition()['type'], $entities);
  }

  /**
   * {@inheritdoc}
   */
  public function execute($object = NULL) {
    $this->executeMultiple([$object]);
  }

  /**
   * {@inheritdoc}
   */
  public function access($object, ?AccountInterface $account = NULL, $return_as_object = FALSE) {
    $result = $object->access('view', $account, TRUE);

    return $return_as_object ? $result : $result->isAllowed();
  }

}
